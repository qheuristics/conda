from __future__ import print_function, division, absolute_import

import os
from collections import defaultdict
from os.path import dirname, isdir, join

from conda import config
from conda import install
#from conda.utils import url_path
from conda.fetch import fetch_index
from conda.compat import iteritems, itervalues
from conda.resolve import Package


def _name_fn(fn):
    assert fn.endswith('.tar.bz2')
    return install.name_dist(fn[:-8])

def _fn2spec(fn):
    assert fn.endswith('.tar.bz2')
    return ' '.join(fn[:-8].rsplit('-', 2))


def get_index(channel_urls=(), prepend=True, platform=None):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    """
    channel_urls = config.normalize_urls(channel_urls, platform=platform)
    if prepend:
        channel_urls += config.get_channel_urls(platform=platform)
    return fetch_index(tuple(channel_urls))


def app_get_index(all_version=False):
    """
    return the index of available applications on the channels

    By default only the latest version of each app is included in the result,
    unless all_version is set to True.
    """
    index = {fn: info for fn, info in iteritems(get_index())
             if info.get('type') == 'app'}
    if all_version:
        return index

    d = defaultdict(list) # name -> list of Package objects
    for fn, info in iteritems(index):
        d[_name_fn(fn)].append(Package(fn, info))

    res = {}
    for pkgs in itervalues(d):
        pkg = max(pkgs)
        res[pkg.fn] = index[pkg.fn]
    return res


def app_get_icon_url(fn):
    """
    return the URL belonging to the icon for application `fn`.
    """
    index = get_index()
    info = index[fn]
    base_url = dirname(info['channel'].rstrip('/'))
    icon_fn = info['icon']
    #icon_cache_path = join(config.pkgs_dir, 'cache', icon_fn)
    #if isfile(icon_cache_path):
    #    return url_path(icon_cache_path)
    return '%s/icons/%s' % (base_url, icon_fn)


def app_info_packages(fn):
    """
    given the filename of a package, return which packages (and their sizes)
    still need to be downloaded, in order to install the package.  That is,
    the package itself and it's dependencies.
    Returns a list of tuples (pkg_name, pkg_version, size,
    fetched? True or False).
    """
    from conda.resolve import Resolve

    index = get_index()
    r = Resolve(index)
    res = []
    for fn2 in r.solve([_fn2spec(fn)]):
        info = index[fn2]
        res.append((info['name'], info['version'], info['size'],
                    any(install.is_fetched(pkgs_dir, fn2[:-8])
                        for pkgs_dir in config.pkgs_dirs)))
    return res


def app_is_installed(fn):
    """
    Return the list of prefix directories in which `fn` in installed into,
    which might be an empty list.
    """
    prefixes = [config.root_dir]
    for envs_dir in config.envs_dirs:
        for fn2 in os.listdir(envs_dir):
            prefix = join(envs_dir, fn2)
            if isdir(prefix):
                prefixes.append(prefix)
    dist = fn[:-8]
    return [prefix for prefix in prefixes if install.is_linked(prefix, dist)]

# It seems to me that we need different types of apps, i.e. apps which
# are preferably installed (or already exist) in existing environments,
# and apps which are more "standalone" (such as firefox).

def app_install(fn, prefix=config.root_dir):
    """
    Install the application `fn` into prefix (which defauts to the root
    environment).
    """
    import conda.plan as plan

    index = get_index()
    actions = plan.install_actions(prefix, index, [_fn2spec(fn)])
    plan.execute_actions(actions, index)


def app_launch(fn, prefix=config.root_dir, additional_args=None):
    """
    Launch the application `fn` (with optional additional command line
    arguments), in the prefix (which defaults to the root environment).
    Returned is the process object (the one returned by subprocess.Popen),
    or None if the application `fn` is not installed in the prefix.
    """
    from conda.misc import launch

    return launch(fn, prefix, additional_args)


def app_uninstall(fn, prefix=config.root_dir):
    """
    Uninstall application `fn` (but not its dependencies).

    Like `conda remove fn`.

    """
    import conda.cli.common as common
    import conda.plan as plan

    index = None
    specs = [_fn2spec(fn)]
    if (plan.is_root_prefix(prefix) and
        common.names_in_specs(common.root_no_rm, specs)):
        raise ValueError("Cannot remove %s from the root environment" %
                         ', '.join(common.root_no_rm))

    actions = plan.remove_actions(prefix, specs)

    if plan.nothing_to_do(actions):
        raise ValueError("Nothing to do")

    plan.execute_actions(actions, index)


if __name__ == '__main__':
    #from pprint import pprint
    for fn in app_get_index():
        print('%s: %s' % (fn, app_is_installed(fn)))
    #pprint(missing_packages('twisted-12.3.0-py27_0.tar.bz2'))
    #print(app_install('twisted-12.3.0-py27_0.tar.bz2'))
    #pprint(get_index())
    #print(app_get_icon_url('spyder-app-2.2.0-py27_0.tar.bz2'))
