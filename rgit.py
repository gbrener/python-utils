#!/usr/bin/env python

"""
Interface with GitHub via the command-line.
"""

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import sys
import argparse
import requests
import json
import shutil
import os
import re

import git    # conda install -c conda-forge gitpython


class Record(dict):
    """
    A container class that allows us to abstract away the GitHub API responses.
    """
    pass


class CommentRecord(Record):
    """
    Give more sensible names (due to loss of generality) to fields and
    ignore metadata from GitHub API that we don't use.
    """
    def __init__(self, comment):
        super(Record, self).__init__()
        self['url'] = comment['html_url']
        self['creator'] = comment['user']['login']
        self['body'] = comment['body']



class IssueRecord(Record):
    """
    Give more sensible names (due to loss of generality) to fields and
    ignore metadata from GitHub API that we don't use.
    """
    def __init__(self, issue):
        super(Record, self).__init__()
        self['id'] = str(issue['number'])
        self['state'] = issue['state']
        self['title'] = issue['title']
        self['url'] = issue['html_url']
        if issue['milestone']:
            self['milestone'] = {
                'title': issue['milestone']['title'],
                'description': issue['milestone']['description'],
                'due_on': issue['milestone']['due_on'],
            }
        else:
            self['milestone'] = {}
        self['creator'] = issue['user']['login']
        self['assignees'] = [assignee['login'] for assignee in issue['assignees']]
        self['labels'] = [label['name'] for label in issue['labels']]
        self['n_comments'] = str(issue['comments'])
        self['body'] = issue['body']


class PullRequestRecord(Record):
    """
    Give more sensible names (due to loss of generality) to fields and
    ignore metadata from GitHub API that we don't use.
    """
    def __init__(self, pr):
        super(Record, self).__init__()
        self['id'] = str(pr['number'])
        self['state'] = pr['state']
        self['merged'] = not not pr['merged_at']
        self['branch'] = pr['head']['ref']
        self['title'] = pr['title']
        self['url'] = pr['html_url']
        self['user'] = pr['user']['login']
        self['base_branch'] = pr['base']['label']
        self['n_comments'] = str(pr.get('comments', 0))
        self['body'] = pr['body']


class DisplayProgress(git.RemoteProgress):
    def update(self, op, cur_count, max_count=None, message=''):
        print('.', end='', flush=True, file=sys.stderr)


def clone_repo(remote_url, dest_dpath):
    progDisplay = DisplayProgress()
    print('Cloning {} into {}'.format(remote_url, dest_dpath), file=sys.stderr)
    git.Repo.clone_from(remote_url, dest_dpath+'.tmp', progress=progDisplay)
    shutil.move(dest_dpath+'.tmp', dest_dpath)
    print('', file=sys.stderr)
    repo = git.Repo(dest_dpath)
    return repo


def checkout_pr(repo, pr_record):
    repo.git.checkout('master')
    repo.git.fetch('origin', 'pull/' + pr_record['id'] + '/head:' + pr_record['branch'])
    print('Checking out branch "{}"'.format(pr_record['branch']), file=sys.stderr)
    repo.git.checkout(pr_record['branch'])


def prepare_session():
    import getpass
    session = requests.Session()
    print('GitHub Username: ', end='', file=sys.stderr)
    gh_username = input()
    gh_password = getpass.getpass(prompt='Password: ', stream=sys.stderr)
    session.auth = (gh_username, gh_password)
    return session


def gh_list(thing, session=None):
    records = []

    if re.search(r'/pulls/\d+/comments$', thing):
        args.list = re.sub(r'/pulls/(\d+/comments)$', r'/issues/\1', thing, count=1)
        # print('Warning: GitHub API treats PR comments as issue comments. Assuming you meant "{}"...'.format(thing), file=sys.stderr)
    url = 'https://api.github.com/repos/' + thing
    # print('GET Request: "{}"...'.format(url), file=sys.stderr)
    if session is None:
        resp = requests.get(url)
    else:
        resp = session.get(url)
    assert resp.status_code == 200, 'Error during GET request to {}'.format(url)

    if '/comment' in thing:
        # Collect metadata about comments
        comment_data = resp.json()
        if isinstance(comment_data, dict):
            comment_data = [comment_data]
        for comment in comment_data:
            record = CommentRecord(comment)
            records.append(record)

    elif '/pull' in thing:
        # Collect metadata about pull requests
        pr_data = resp.json()
        if isinstance(pr_data, dict):
            pr_data = [pr_data]
        for pr in pr_data:
            record = PullRequestRecord(pr)
            records.append(record)

    elif '/issue' in thing:
        # Collect metadata about issues
        issue_data = resp.json()
        if isinstance(issue_data, dict):
            issue_data = [issue_data]
        for issue in issue_data:
            record = IssueRecord(issue)
            records.append(record)

    return records


def gh_checkout(thing, session=None):
    url = 'https://api.github.com/repos/' + thing
    if session is None:
        resp = requests.get(url)
    else:
        resp = session.get(url)
    assert resp.status_code == 200, 'Error during GET request to {}'.format(url)

    pr_info = resp.json()
    pr_record = PullRequestRecord(pr_info)
    dest_dpath = '/tmp/' + thing
    try:
        repo = git.Repo(dest_dpath)
        print('Found existing repo at "{}"'.format(dest_dpath), file=sys.stderr)
    except git.exc.NoSuchPathError:
        dest_parent_dpath = os.path.dirname(dest_dpath)
        if not os.path.isdir(dest_parent_dpath):
            os.makedirs(dest_parent_dpath)
        repo = clone_repo(pr_info['base']['repo']['clone_url'], dest_dpath)

    checkout_pr(repo, pr_record)
    return repo


def main(argv):
    parser = argparse.ArgumentParser()
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument('-l', '--list', help='List PRs and/or issues. e.g. ContinuumIO/elm/pulls, ContinuumIO/elm/issues')
    grp.add_argument('-c', '--checkout', help='Checkout a PR based on the ID. e.g. ContinuumIO/elm/pulls/192')
    # TODO: Add "respond" feature
    # grp.add_argument('-r', '--respond', help='Respond to a PR comment-thread or issue-thread. e.g. ContinuumIO/elm/pulls/192, ContinuumIO/elm/issues/192')
    args = parser.parse_args(argv[1:])

    session = prepare_session()

    if args.list is not None:
        records = gh_list(args.list, session=session)
        print(json.dumps(records, indent=4))

    elif args.checkout is not None:
        gh_checkout(args.checkout, session=session)

    # TODO: Add "respond" feature
    # elif args.respond is not None:
    #     pass


if __name__ == '__main__':
    sys.exit(main(sys.argv))
