import git
import difflib
import time
import datetime
import logging
from tqdm import tqdm
from csv_parser import fill_data
import init_bd
from init_bd import BlockedIpData, engine
from geodata_loader import load_some_geodata
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update

logger = logging.getLogger(__name__)
Session = sessionmaker(bind=engine)
fh = logging.FileHandler('errors.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)

def get_changes(repo_path):
    repo = git.Repo(repo_path)
    for remote in repo.remotes:
        remote.fetch()
    fetched = list(repo.iter_commits('HEAD..origin'))
    print('{0} commits are fetched!'.format(len(fetched)))
    d = difflib.Differ()
    fetched.reverse()
    for commit in fetched:
        assert(len(commit.parents) == 1) # linear repo
        prev = commit.parents[0]
        try:
            diffs = prev.diff(commit, paths='dump.csv', 
                          create_patch=True, ignore_blank_lines=True, 
                          ignore_space_at_eol=True, diff_filter='cr')
        except Exception as e:
            logger.error('{0}\t{1}\t{2}'.format(commit, prev, e))
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
    for remote in repo.remotes:
        remote.pull()

def update(repo, session): 
    for commit, added, removed in tqdm(get_changes(repo)):
        date = datetime.datetime.fromtimestamp(commit.committed_date).strftime('%Y-%m-%d')
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
        print(commit, date, len(added), len(removed), len(added_ip_clean), len(removed_ip_clean))
        for added in map(dict, added_ip_clean):
            added['include_time'] = date
            added['exclude_time'] = None
            try:
                if added['ip']:
                    obj = session.query(BlockedIpData).filter_by(ip=added['ip'], 
                        org=added['org'], decision_date=added['decision_date'], 
                        decision_number=added['decision_number']) 
                elif added['ip_subnet']:
                    obj = session.query(BlockedIpData).filter_by(ip_subnet=added['ip_subnet'], 
                        org=added['org'], decision_date=added['decision_date'], 
                        decision_number=added['decision_number'])
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
                logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, added, e))
        for removed in map(dict, removed_ip_clean):
            try:
                if removed['ip']:
                    obj = session.query(BlockedIpData).filter_by(ip=removed['ip'], 
                        org=removed['org'], decision_date=removed['decision_date'], 
                        decision_number=removed['decision_number']) 
                elif removed['ip_subnet']:
                    obj = session.query(BlockedIpData).filter_by(ip_subnet=removed['ip_subnet'], 
                        org=removed['org'], decision_date=removed['decision_date'], 
                        decision_number=removed['decision_number'])
                else:
                    raise Exception("Bad ip data: " + str(removed))
                if obj.first():
                    obj.update({'exclude_time': date})
                else:
                    raise Exception("Bad ip data: " + str(removed))
            except Exception as e:
                logger.error('{0}\t{1}\t{2}\t{3}'.format(commit, date, removed, e))
        session.commit()


if __name__ == '__main__':
    session = Session()
    update('../z-i/', session)