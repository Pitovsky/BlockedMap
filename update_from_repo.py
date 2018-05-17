# -*- coding: utf-8 -*-

import git
import difflib
import time
import datetime
import logging
import os
from tqdm import tqdm
from csv_parser import fill_data
from collections import defaultdict
import init_db
import pickle
from init_db import BlockedIpData, Stats, engine, get_bin_prefix
from ip_selector import full_geo_cache, select_ip
from geodata_loader import load_some_geodata
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from ipaddress import ip_network, ip_address  

Session = sessionmaker(bind=engine)
BASEDIR = os.path.abspath(os.path.dirname(__file__))
repo_path = os.path.join(BASEDIR, '../z-i/')

logger = logging.getLogger('errors')
logger_info = logging.getLogger(__name__)
# only errors here
fh = logging.FileHandler(os.path.join(BASEDIR, 'errors.log'))
fh.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S')
# everything is written here
fh_all = logging.FileHandler(os.path.join(BASEDIR, 'update.log'))
fh_all.setLevel(logging.INFO)
fh_all.setFormatter(formatter)
# piping everything to console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger_info.addHandler(fh_all)
logger_info.addHandler(ch)


def count_network_ips(subnet):
    prefix = get_bin_prefix(ip_network(addresses[block_id]))
    return 2 << (31 - len(prefix))


class DayStats:
    def __init__(self):
        self.blocked = defaultdict(int)
        self.unlocked = defaultdict(int)


def get_changes(repo_path, squash=False):
    repo = git.Repo(repo_path)
    repo.remotes.origin.fetch()
    fetched = list(repo.iter_commits('HEAD..origin'))
    logger_info.info('{0} commits are fetched!'.format(len(fetched)))
    logger_info.info('Head is now at {0}.'.format(repo.heads.master.commit))
    fetched.reverse()
    squashed_commits = []
    everything_alright = True
    parent = repo.heads.master.commit
    for commit, next_commit in zip(fetched, fetched[1:]):
        assert(len(commit.parents) == 1) # linear repo
        if not squash:
            squashed_commits.append((commit.parents[0], commit))
            parent = commit
            continue
        if datetime.datetime.fromtimestamp(commit.committed_date).day != datetime.datetime.fromtimestamp(next_commit.committed_date).day:
            squashed_commits.append((parent, commit))
            parent = commit
    if squash:
        logger_info.info('Squashed: {0} diffs are compared!'.format(len(squashed_commits)))
    d = difflib.Differ()
    for prev, commit in squashed_commits:
        try:
            diffs = prev.diff(commit, paths='dump.csv', 
                          create_patch=True, ignore_blank_lines=True, 
                          ignore_space_at_eol=True, diff_filter='cr')
        except Exception as e:
            logger.error('{0}\t{1}\t{2}'.format(commit, prev, e))
            continue
        if len(diffs) == 0:
            continue
        assert(len(diffs) == 1)
        added, removed = [], []
        added.clear()
        removed.clear()
        diff = diffs[0]
        for line in diff.diff.decode('cp1251').split('\n'):
            if line.startswith('+'):
                added.append(line)
            if line.startswith('-'):
                removed.append(line)
        yield commit, added, removed
    if everything_alright:
        repo.heads.master.set_commit(parent)
        repo.heads.master.checkout(force=True)
        logger_info.info('Head is now at {0}, {1} commits behind origin.'.format(repo.heads.master.commit, len(list(repo.iter_commits('HEAD..origin')))))


def gen_clean_ips(repo):
    for commit, added, removed in tqdm(get_changes(repo, True)):
        date = datetime.datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d')
        removed_ip, added_ip = set(), set()
        
        for removed_diff in removed:
            try:
                if removed_diff.startswith('-Updated: '):
                    continue
                for data in fill_data(removed_diff.strip('-').split(';')):
                    removed_ip.add(tuple(data.items()))
            except:
                everything_alright = False
                logger.error('{0}\t{1}\t{2}'.format(commit, date, removed_diff))
        
        for added_diff in added:
            try:
                if added_diff.startswith('+Updated: '):
                    continue
                for data in fill_data(added_diff.strip('+').split(';')):
                    added_ip.add(tuple(data.items()))
            except Exception as e:
                everything_alright = False
                logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added_diff, e))
        added_ip_clean = added_ip - removed_ip
        removed_ip_clean = removed_ip - added_ip
        logger_info.info('{} {} {} {} {} {}'.format(commit, date, len(added_ip), len(removed_ip), len(added_ip_clean), len(removed_ip_clean)))
        assert(len(added_ip) - len(added_ip_clean) == len(removed_ip) - len(removed_ip_clean))
        yield date, commit, map(dict, added_ip_clean), map(dict, removed_ip_clean) 


def update_geodata(session, added_ips, removed_ips, date, commit):
    for added in added_ips:
        added['include_time'] = date
        added['exclude_time'] = None
        try:
            if added['ip']:
                obj = session.query(BlockedIpData).filter_by(ip=added['ip'], 
                    org=added['org'], decision_date=added['decision_date']) 
            elif added['ip_subnet']:
                obj = session.query(BlockedIpData).filter_by(ip_subnet=added['ip_subnet'], 
                            org=added['org'], decision_date=added['decision_date'])
            else:
                raise Exception("Bad ip data: " + str(added))
            if obj.first():
                excluded = obj.filter(BlockedIpData.exclude_time!=None)
                if excluded.first():
                    excluded.update({'exclude_time': None})
            else:
                blocked_ip = BlockedIpData(added)
                session.add(blocked_ip)
                session.flush()
                if blocked_ip.ip:
                    load_some_geodata(session, {blocked_ip.id: blocked_ip.ip})
                else:
                    load_some_geodata(session, {blocked_ip.id: blocked_ip.ip_subnet}, True)
        except Exception as e:
            everything_alright = False
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added, e))
    
    for removed in removed_ips:
        try:
            if removed['ip']:
                obj = session.query(BlockedIpData).filter_by(ip=removed['ip'], 
                    org=removed['org'], decision_date=removed['decision_date']) 
            elif removed['ip_subnet']:
                obj = session.query(BlockedIpData).filter_by(ip_subnet=removed['ip_subnet'], 
                    org=removed['org'], decision_date=removed['decision_date'])
            else:
                raise Exception("Bad ip data: " + str(removed))
            if obj.first():
                obj.update({'exclude_time': date})
            else:
                raise Exception("Bad ip data: " + str(removed))
        except Exception as e:
            everything_alright = False
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, removed, e))


def update_stats(session, added_ips, removed_ips, date, commit):
    stats = DayStats()
    for added in added_ips:
        try:
            if added['ip']:
                if added['org']:
                    stats.blocked[added['org']] += 1
            elif added['ip_subnet']:
                if added['org']:
                    stats.blocked[added['org']] += count_network_ips(added['ip_subnet'])
            else:
                raise Exception("Bad ip data: " + str(added))
        except Exception as e:
            everything_alright = False
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added, e))
    
    for removed in removed_ips:
        try:
            if removed['ip']:
                if removed['org']:
                    stats.unlocked[added['org']] += 1
            elif removed['ip_subnet']:
                if removed['org']:
                    stats.unlocked[added['org']] += count_network_ips(removed['ip_subnet'])
            else:
                raise Exception("Bad ip data: " + str(removed))
        except Exception as e:
            everything_alright = False
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, removed, e))
    
    for org in set(stats.blocked.keys()) | set(stats.unlocked.keys()):
        session.add(Stats(date, stats.blocked[org], stats.unlocked[org], org))
        

def update(repo, session): 
    for date, commit, added_ip_clean, removed_ip_clean in gen_clean_ips(repo):
        update_geodata(session, added_ip_clean, removed_ip_clean, date, commit)
        update_stats(session, added_ip_clean, removed_ip_clean, date, commit)
        
        try:
            session.commit()
        except Exception as e:
            everything_alright = False
            logger.error('Commit failed: {0}\t{1}'.format(commit, date))


def get_repo_state():
    return git.Repo(repo_path).heads.master.commit


def make_cache():
    with open(full_geo_cache, 'wb') as cache:
        pickle.dump(select_ip(use_cache=False), cache)


if __name__ == '__main__':
    session = Session()
    update(repo_path, session)
    make_cache()
    
