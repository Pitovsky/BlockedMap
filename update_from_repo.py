import git
import difflib
import time

def generate_diffs(repo_path):
    repo = git.Repo(repo_path)
    for remote in repo.remotes:
        remote.fetch()
    fetched = list(repo.iter_commits('HEAD..origin'))
    print('{0} commits are fetched!'.format(len(fetched)))
    d = difflib.Differ()
    for commit in fetched:
        assert(len(commit.parents) == 1) # linear repo
        prev = commit.parents[0]
        diffs = prev.diff(commit, paths='dump.csv', 
                          create_patch=True, ignore_blank_lines=True, 
                          ignore_space_at_eol=True, diff_filter='cr')
        assert(len(diffs) == 1)
        added, removed = [], []
        diff = diffs[0]
        for line in diff.diff.decode('cp1251').split('\n'):
            if line.startswith('+'):
                added.append(line)
            if line.startswith('-'):
                removed.append(line)
        yield commit, added, removed
        
for commit, added, removed in generate_diffs('../z-i/'):
    print(commit, len(added), len(removed))
    