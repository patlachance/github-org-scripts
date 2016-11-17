#!/usr/bin/env python
"""
    Report on Service & Web hooks for organization.
"""
import argparse
import client
import logging
import urlparse
import yaml

"""
    Lore:   swapping hook.test for hook.ping will cause repetition of the
            actions.  In particular, a number of repos post to IRC channels
            and/or bugs on commits, so expect comments to that effect.
"""

logger = logging.getLogger(__name__)


def report_hooks(gh, org, active_only, unique_only, do_ping, yaml_out):
    org_handle = gh.organization(org)
    org_struct = org_handle.as_dict()
    repo_list = []
    org_struct['repo_list'] = repo_list
    unique_hooks = set()
    msg = "Active" if active_only else "All"
    for repo in org_handle.repositories():
        repo_struct = repo.as_dict()
        hook_list = []
        repo_struct['hook_list'] = hook_list
        repo_list.append(repo_struct)
        repo_hooks = set()
        ping_attempts = ping_fails = 0
        for hook in repo.hooks():
            hook_struct = hook.as_dict()
            hook_list.append(hook_struct)
            # if hook.name == "web", then this is a web hook, and there can be
            # several per repo. The unique part is the hook.config['url'], which
            # may contain sensitive info (including basic login data), so just
            # grab scheme, hostname, and port.
            if hook.name != "web":
                name = hook.name
            else:
                url = hook.config['url']
                parts = urlparse.urlparse(url)
                # port can be None, which prints funny, but is good enough for
                # identification.
                name = "%s://%s:%s" % (parts.scheme, parts.hostname, parts.port)
            if hook.active or not active_only:
                repo_hooks.add(name)
            if do_ping and hook.active:
                ping_attempts += 1
                if not hook.ping():
                    ping_fails += 1
                    logger.warning('Ping failed for %s', name)
        if repo_hooks and not unique_only:
            print("%s hooks for %s, pinged %d (%d failed)" % (msg, repo.name,
                                                              ping_attempts,
                                                              ping_fails))
            for h in repo_hooks:
                print(h)
        unique_hooks = unique_hooks.union(repo_hooks)
    if yaml_out:
        print(yaml.safe_dump([org_struct, ]))
    elif unique_only and unique_hooks:
        print("%s hooks for org %s" % (msg, org))
        for h in unique_hooks:
            print(h)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("org", help='Organization', default=['mozilla'],
                        nargs='*')
    parser.add_argument("--active", help="Show active hooks only",
                        action='store_true')
    parser.add_argument("--unique", help="Show unique hook names only",
                        action='store_true')
    parser.add_argument("--ping", help="Ping all hooks", action="store_true")
    parser.add_argument("--yaml", help="Yaml ouput only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    gh = client.get_github3_client()
    for org in args.org:
        report_hooks(gh, org, args.active, args.unique, args.ping, args.yaml)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    logging.getLogger('github3').setLevel(logging.WARNING)
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit