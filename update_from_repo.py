# -*- coding: utf-8 -*-

from collections import defaultdict
import difflib
from ipaddress import ip_address, ip_network
import logging
import os
import pickle

import git
from tqdm import tqdm
from csv_parser import fill_data
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update

from init_db import BlockedIpData, Stats, engine, get_bin_prefix, get_bin_ip
from ip_selector import full_geo_cache, select_ip
from geodata_loader import load_some_geodata

Session = sessionmaker(bind=engine)
BASEDIR = os.path.abspath(os.path.dirname(__file__))
LOGSDIR = BASEDIR + '/logs/'
repo_path = os.path.join(BASEDIR, '../z-i/')
report_threshold = 5000

os.makedirs(LOGSDIR, exist_ok=True)

logger = logging.getLogger('errors')
logger_info = logging.getLogger('update')
# only errors here
fh = logging.FileHandler(os.path.join(LOGSDIR, 'errors.log'))
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                              datefmt='%Y-%m-%d %H:%M:%S')
# everything is written here
fh_all = logging.FileHandler(os.path.join(LOGSDIR, 'update.log'))
fh_all.setFormatter(formatter)
# piping everything to console
ch = logging.StreamHandler()
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.setLevel(logging.ERROR)
logger_info.addHandler(fh_all)
logger_info.addHandler(ch)
logger_info.setLevel(logging.DEBUG)


def count_network_ips(subnet):
    prefix = get_bin_prefix(ip_network(subnet))
    return 2 << (31 - len(prefix))


class DayStats:
    def __init__(self, date):
        self.blocked = defaultdict(int)
        self.unlocked = defaultdict(int)
        self.no_org = 0
        self.date = date

    def __str__(self):
        return '<DayStats {}> blocked: {}, unlocked: {}, not counted: {}'.format(self.date, sum(self.blocked.values()), sum(self.unlocked.values()), self.no_org)


def get_commit_date(commit):
    # datetime.datetime.fromtimestamp(commit.authored_date).strftime('%Y-%m-%d')
    return commit.message.split(' ')[1]


def get_changes(repo_path, squash=False):
    repo = git.Repo(repo_path)
    # repo.remotes.origin.fetch()
    fetched = list(repo.iter_commits('HEAD..origin'))
    logger_info.warning('{0} commits are fetched!'.format(len(fetched)))
    logger_info.info('Head is now at {0}.'.format(repo.heads.master.commit))
    fetched.reverse()
    squashed_commits = []
    last_processed_commit = parent = repo.head.commit

    for commit, next_commit in zip(fetched, fetched[1:]):
        assert len(commit.parents) == 1 # linear repo
        if not squash:
            squashed_commits.append((commit.parents[0], commit))
            parent = commit
            continue
        if get_commit_date(commit) != get_commit_date(next_commit):
            squashed_commits.append((parent, commit))
            parent = commit
    if squash:
        logger_info.info('Squashed: {0} diffs are compared!'.format(len(squashed_commits)))

    for prev, commit in squashed_commits:
        try:
            diffs = prev.diff(commit, paths='dump.csv',
                              create_patch=True, ignore_blank_lines=True,
                              ignore_space_at_eol=True, diff_filter='cr')
        except Exception as e:
            logger.error('Error while calculating diff for {0}\t{1}\t{2}'.format(commit, prev, e))
            continue
        if len(diffs) == 0:
            continue
        assert len(diffs) == 1
        added, removed = [], []
        added.clear()
        removed.clear()
        diff = diffs[0]
        for line in diff.diff.decode('cp1251').split('\n'):
            if line.startswith('+'):
                added.append(line)
            if line.startswith('-'):
                removed.append(line)
        yield prev, commit, added, removed
        last_processed_commit = commit
    repo.heads.master.set_commit(last_processed_commit)
    repo.heads.master.checkout(force=True)
    logger_info.info('Head is now at {0}, {1} commits behind origin.'.format(repo.heads.master.commit, len(list(repo.iter_commits('HEAD..origin')))))


def report(prev, commit, added_ip_clean, removed_ip_clean):
    date = get_commit_date(commit)
    with open(LOGSDIR + 'report_{0}.log'.format(date), 'w') as f:
        f.write('{0} --> {1} (+ {2}, - {3})\n'.format(prev, commit, len(added_ip_clean), len(removed_ip_clean)))
        commits = list(git.Repo(repo_path).iter_commits('{0}..{1}'.format(prev, commit)))
        for c in commits:
            dump = c.stats.files.get('dump.csv')
            if dump:
                f.write('{0}\t+{1}\t-{2}\n'.format(c, dump['insertions'], dump['deletions']))
            else:
                f.write('{0}\t{1}\n'.format(c, c.stats.files))


def gen_clean_ips(repo):
    for prev, commit, added, removed in tqdm(get_changes(repo, True)):
        date = get_commit_date(commit)
        removed_ip, added_ip = set(), set()

        for removed_diff in removed:
            try:
                if removed_diff.startswith('-Updated: '):
                    continue
                for data in fill_data(removed_diff.strip('-').split(';')):
                    removed_ip.add(tuple(data.items()))
            except:
                logger.error('{0}\t{1}\t{2}'.format(commit, date, removed_diff))

        for added_diff in added:
            try:
                if added_diff.startswith('+Updated: '):
                    continue
                for data in fill_data(added_diff.strip('+').split(';')):
                    added_ip.add(tuple(data.items()))
            except Exception as e:
                logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added_diff, e))
        added_ip_clean = added_ip - removed_ip
        removed_ip_clean = removed_ip - added_ip
        logger_info.info('{} {} {} {} {} {}'.format(commit, date, len(added_ip), len(removed_ip), len(added_ip_clean), len(removed_ip_clean)))
        if len(added_ip_clean) > report_threshold or len(removed_ip_clean) > report_threshold:
            report(prev, commit, added_ip_clean, removed_ip_clean)
        assert len(added_ip) - len(added_ip_clean) == len(removed_ip) - len(removed_ip_clean)
        yield date, commit, list(map(dict, added_ip_clean)), list(map(dict, removed_ip_clean))


def update_geodata(session, added_ips, removed_ips, date, commit):
    for added in added_ips:
        added['include_time'] = date
        added['exclude_time'] = None
        try:
            if added['ip']:
                ip_bin = get_bin_ip(ip_address(added['ip']))
            elif added['ip_subnet']:
                ip_bin = get_bin_prefix(ip_network(added['ip_subnet']))
            else:
                raise Exception("Bad ip added: " + str(added))
            obj = session.query(BlockedIpData).filter_by(
                ip_bin=ip_bin,
                org=added['org'],
                decision_date=added['decision_date'],
            )
            if obj.first():
                excluded = obj.filter(BlockedIpData.exclude_time is not None)
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
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added, e))

    for removed in removed_ips:
        try:
            if removed['ip']:
                ip_bin = get_bin_ip(ip_address(removed['ip']))
            elif removed['ip_subnet']:
                ip_bin = get_bin_prefix(ip_network(removed['ip_subnet']))
            else:
                raise Exception("Bad ip removed: " + str(removed))
            obj = session.query(BlockedIpData).filter_by(
                ip_bin=ip_bin,
                org=removed['org'],
                decision_date=removed['decision_date'],
            )
            if obj.first():
                obj.update({'exclude_time': date})
            else:
                raise Exception("Removed ip not found: " + str(removed))
        except Exception as e:
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, removed, e))


def update_stats(session, added_ips, removed_ips, date, commit):
    stats = DayStats(date)
    logger_info.info('added_ips: {}, removed_ips: {}, date: {}, commit: {}'.format(len(added_ips), len(removed_ips), date, commit))

    for added in added_ips:
        try:
            if added['ip']:
                if added['org']:
                    stats.blocked[added['org']] += 1
                else:
                    stats.no_org += 1
            elif added['ip_subnet']:
                if added['org']:
                    stats.blocked[added['org']] += count_network_ips(added['ip_subnet'])
                else:
                    stats.no_org += count_network_ips(added['ip_subnet'])
            else:
                raise Exception("Bad ip org data added: " + str(added))
        except Exception as e:
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added, e))

    for removed in removed_ips:
        try:
            if removed['ip']:
                if removed['org']:
                    stats.unlocked[removed['org']] += 1
                else:
                    stats.no_org += 1
            elif removed['ip_subnet']:
                if removed['org']:
                    stats.unlocked[removed['org']] += count_network_ips(removed['ip_subnet'])
                else:
                    stats.no_org += count_network_ips(removed['ip_subnet'])
            else:
                raise Exception("Bad ip org data removed: " + str(removed))
        except Exception as e:
            logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, removed, e))

    logger_info.info(str(stats))
    for org in set(stats.blocked.keys()) | set(stats.unlocked.keys()):
        session.add(Stats(date, stats.blocked[org], stats.unlocked[org], org))


def db_update(repo, session):
    for date, commit, added_ip_clean, removed_ip_clean in gen_clean_ips(repo):
        update_geodata(session, added_ip_clean, removed_ip_clean, date, commit)
        update_stats(session, added_ip_clean, removed_ip_clean, date, commit)

        try:
            session.commit()
        except Exception as e:
            logger.error('Commit failed: {0}\t{1}'.format(commit, date))
            raise


def get_repo_state():
    return git.Repo(repo_path).heads.master.commit


def make_cache():
    with open(full_geo_cache, 'wb') as cache:
        pickle.dump(select_ip(use_cache=False), cache)


if __name__ == '__main__':
    session = Session()
    db_update(repo_path, session)
    make_cache()
