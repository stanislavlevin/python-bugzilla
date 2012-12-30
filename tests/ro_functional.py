#
# Copyright Red Hat, Inc. 2012
#
# This work is licensed under the terms of the GNU GPL, version 2 or later.
# See the COPYING file in the top-level directory.
#

'''
Unit tests that do readonly functional tests against real bugzilla instances.
'''

import unittest

import bugzilla
from bugzilla import Bugzilla

import tests


class BaseTest(unittest.TestCase):
    url = None
    bzclass = Bugzilla
    closestatus = "CLOSED"

    def clicomm(self, argstr, expectexc=False):
        comm = "bugzilla " + argstr

        bz = self.bzclass(url=self.url, cookiefile=None)
        if expectexc:
            self.assertRaises(RuntimeError, tests.clicomm, comm, bz)
        else:
            return tests.clicomm(comm, bz)

    def _testBZClass(self):
        bz = Bugzilla(url=self.url, cookiefile=None)
        self.assertTrue(isinstance(bz, self.bzclass))

    # Since we are running these tests against bugzilla instances in
    # the wild, we can't depend on certain data like product lists
    # remaining static. Use lax sanity checks in this case

    def _testInfoProducts(self, mincount, expectstr):
        out = self.clicomm("info --products").splitlines()
        self.assertTrue(len(out) >= mincount)
        self.assertTrue(expectstr in out)

    def _testInfoComps(self, comp, mincount, expectstr):
        out = self.clicomm("info --components \"%s\"" % comp).splitlines()
        self.assertTrue(len(out) >= mincount)
        self.assertTrue(expectstr in out)

    def _testInfoVers(self, comp, mincount, expectstr):
        out = self.clicomm("info --versions \"%s\"" % comp).splitlines()
        self.assertTrue(len(out) >= mincount)
        if expectstr:
            self.assertTrue(expectstr in out)

    def _testInfoCompOwners(self, comp, expectstr):
        expectexc = (expectstr == "FAIL")
        out = self.clicomm("info --component_owners \"%s\"" %
                           comp, expectexc=expectexc)
        if expectexc:
            return

        self.assertTrue(expectstr in out.splitlines())

    def _testQuery(self, args, mincount, expectbug):
        expectexc = (expectbug == "FAIL")
        cli = "query %s --bug_status %s" % (args, self.closestatus)
        out = self.clicomm(cli, expectexc=expectexc)
        if expectexc:
            return

        self.assertTrue(len(out) >= mincount)
        self.assertTrue(any([l.startswith("#" + expectbug)
                             for l in out.splitlines()]))

        # Check --ids output option
        out2 = self.clicomm(cli + " --ids")
        self.assertTrue(len(out.splitlines()) == len(out2.splitlines()))
        self.assertTrue(any([l == expectbug for l in out2.splitlines()]))


    def _testQueryFull(self, bugid, mincount, expectstr):
        out = self.clicomm("query --full --bug_id %s" % bugid)
        self.assertTrue(len(out.splitlines()) >= mincount)
        self.assertTrue(expectstr in out)

    def _testQueryRaw(self, bugid, mincount, expectstr):
        out = self.clicomm("query --raw --bug_id %s" % bugid)
        self.assertTrue(len(out.splitlines()) >= mincount)
        self.assertTrue(expectstr in out)

    def _testQueryOneline(self, bugid, expectstr):
        out = self.clicomm("query --oneline --bug_id %s" % bugid)
        self.assertTrue(len(out.splitlines()) == 3)
        self.assertTrue(out.splitlines()[2].startswith("#%s" % bugid))
        self.assertTrue(expectstr in out)

    def _testQueryExtra(self, bugid, expectstr):
        out = self.clicomm("query --extra --bug_id %s" % bugid)
        self.assertTrue(("#%s" % bugid) in out)
        self.assertTrue(expectstr in out)

    def _testQueryFormat(self, args, expectstr):
        out = self.clicomm("query %s" % args)
        self.assertTrue(expectstr in out)

    def _testQueryURL(self, url, count, expectstr):
        out = self.clicomm("query --from-url \"%s\"" % url)
        self.assertEqual(len(out.splitlines()), count)
        self.assertTrue(expectstr in out)


class BZ32(BaseTest):
    url = "https://bugzilla.kernel.org/xmlrpc.cgi"
    bzclass = bugzilla.Bugzilla32

    test0 = BaseTest._testBZClass
    test1 = lambda s: BaseTest._testInfoProducts(s, 10, "Virtualization")
    test2 = lambda s: BaseTest._testInfoComps(s, "Virtualization", 3, "kvm")
    test3 = lambda s: BaseTest._testInfoVers(s, "Virtualization", 0, None)
    test4 = lambda s: BaseTest._testInfoCompOwners(s, "Virtualization", "FAIL")

    # Querying was only supported as of bugzilla 3.4
    test5 = lambda s: BaseTest._testQuery(s, "--product Virtualization",
                                          0, "FAIL")


class BZ34(BaseTest):
    url = "https://bugzilla.gnome.org/xmlrpc.cgi"
    bzclass = bugzilla.Bugzilla34
    closestatus = "RESOLVED"

    test0 = BaseTest._testBZClass
    test1 = lambda s: BaseTest._testQuery(s,
                "--product dogtail --component sniff",
                9, "321654")
    # BZ < 4 doesn't report values for --full
    test2 = lambda s: BaseTest._testQueryRaw(s, "321654", 70,
                                             "ATTRIBUTE[version]: CVS HEAD")
    test3 = lambda s: BaseTest._testQueryOneline(s, "321654", "Sniff")


class BZ42(BaseTest):
    url = "https://bugzilla.freedesktop.org/xmlrpc.cgi"
    bzclass = bugzilla.Bugzilla4
    closestatus = "CLOSED,RESOLVED"

    test0 = BaseTest._testBZClass

    test1 = lambda s: BaseTest._testQuery(s, "--product avahi", 10, "3450")
    test2 = lambda s: BaseTest._testQueryFull(s, "3450", 10, "Blocked: \n")
    test2 = lambda s: BaseTest._testQueryRaw(s, "3450", 70,
                                    "ATTRIBUTE[creator]: daniel@fooishbar.org")
    test3 = lambda s: BaseTest._testQueryOneline(s, "3450",
                                    "daniel@fooishbar.org libavahi")
    test4 = lambda s: BaseTest._testQueryExtra(s, "3450", "Error")
    test5 = lambda s: BaseTest._testQueryFormat(s,
                "--bug_id 3450 --outputformat "
                "\"%{bug_id} %{assigned_to} %{summary}\"",
                "3450 daniel@fooishbar.org Error")


class RHTest(BaseTest):
    url = "https://bugzilla.redhat.com/xmlrpc.cgi"
    bzclass = bugzilla.RHBugzilla

    test0 = BaseTest._testBZClass
    test1 = lambda s: BaseTest._testInfoProducts(s, 125,
                                                 "Virtualization Tools")
    test2 = lambda s: BaseTest._testInfoComps(s, "Virtualization Tools",
                                              10, "virt-manager")
    test3 = lambda s: BaseTest._testInfoVers(s, "Fedora", 19, "rawhide")
    test4 = lambda s: BaseTest._testInfoCompOwners(s, "Virtualization Tools",
                                        "libvirt: Libvirt Maintainers")

    test5 = lambda s: BaseTest._testQuery(s,
                "--product Fedora --component python-bugzilla --version 14",
                6, "621030")
    test6 = lambda s: BaseTest._testQueryFull(s, "621601", 60,
                                              "end-of-life (EOL)")
    test7 = lambda s: BaseTest._testQueryRaw(s, "663674", 70,
                "ATTRIBUTE[whiteboard]: whiteboard test")
    test8 = lambda s: BaseTest._testQueryOneline(s, "307471",
                "[---] needinfo?")
    test9 = lambda s: BaseTest._testQueryExtra(s, "307471",
            " +Status Whiteboard:  bzcl34nup")
    test10 = lambda s: BaseTest._testQueryFormat(s,
            "--bug_id 307471 --outputformat=\"id=%{bug_id} "
            "sw=%{whiteboard:status} needinfo=%{flag:needinfo} "
            "sum=%{summary}\"",
            "id=307471 sw= bzcl34nup")
    test11 = lambda s: BaseTest._testQueryURL(s,
            "https://bugzilla.redhat.com/buglist.cgi?f1=creation_ts"
            "&list_id=973582&o1=greaterthaneq&classification=Fedora&"
            "o2=lessthaneq&query_format=advanced&f2=creation_ts"
            "&v1=2010-01-01&component=python-bugzilla&v2=2011-01-01"
            "&product=Fedora", 26, "#553878 CLOSED")

    def testQueryFixedIn(self):
        out = self.clicomm("query --fixed_in anaconda-15.29-1")
        self.assertEquals(len(out.splitlines()), 6)
        self.assertTrue("#629311 CLOSED" in out)