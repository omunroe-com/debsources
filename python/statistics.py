# Copyright (C) 2013-2014  Stefano Zacchiroli <zack@upsilon.cc>
#
# This file is part of Debsources.
#
# Debsources is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Compute several statistics about Debsouces content

"""

from sqlalchemy import distinct
from sqlalchemy import func as sql_func

from models import Checksum, Ctag, Metric, SlocCount, SuitesMapping, Version


def _count(query):
    count = query.first()[0]
    if not count:
        count = 0
    return count


def _time_series(query):
    return [ (row['timestamp'], row['value']) for row in query ]


def suites(session):
    return [ row[0] for row in session.query(distinct(SuitesMapping.suite)) ]


def disk_usage(session, suite=None):
    """disk space used by extracted source packages

    only count disk usage relative to suite, if given

    """
    q = session.query(sql_func.sum(Metric.value)) \
               .filter(Metric.metric == 'size')
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)
    return _count(q)


def source_packages(session, suite=None):
    """(versioned) source package count

    only count packages in suite, if given

    multiple versions of the same source package count adds up to the result of
    this query. When doing per-suite queries that doesn't (shouldn't) happen,
    as each suite is (usually) guaranteed to contain at most one version of
    each packages

    """
    q = session.query(sql_func.count(Version.id))
    if suite:
        q = q.join(SuitesMapping) \
            .filter(SuitesMapping.suite == suite)
    return _count(q)


def source_files(session, suite=None):
    """source files count

    only count source files in suite, if given

    Return 0 if the checksum plugin is not enabled

    """
    # TODO when a separate File table will be present, this will need to be
    # adapted to use that instead of Checksum
    q = session.query(sql_func.count(Checksum.id))
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)
    return _count(q)


def sloccount_lang(session, language, suite=None):
    """source lines of codes (SLOCs) written in a given programming language

    only count SLOCs relative to suite, if given

    """
    q = session.query(sql_func.sum(SlocCount.count)) \
               .filter(SlocCount.language == language)
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)
    return _count(q)


def sloccount_summary(session, suite=None):
    """source lines of code (SLOCs), broken down per language

    return a language-indexed dictionary of SLOC counts

    only count LOCs relative to suite, if given

    """
    q = session.query(SlocCount.language, sql_func.sum(SlocCount.count))
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)
    q = q.group_by(SlocCount.language)
    return dict(q.all())


def ctags(session, suite=None):
    """ctags count

    only count ctags in suite, if given

    """
    q = session.query(sql_func.count(Ctag.id))
    if suite:
        q = q.join(Version) \
             .join(SuitesMapping) \
             .filter(SuitesMapping.suite == suite)
    return _count(q)


def _hist_size_sample(session, metric, interval, projection, suite=None):
    q = "\
      SELECT DISTINCT ON (%(projection)s) timestamp, %(metric)s AS VALUE \
      FROM history_size \
      WHERE timestamp >= now() - interval '%(interval)s' \
      %(filter)s \
      ORDER BY %(projection)s DESC, timestamp DESC"
    kw = { 'metric': metric,
           'projection': projection,
           'interval': interval,
           'filter': '' }
    if suite:
        kw['filter'] = "AND suite = '%s'" % suite
    return _time_series(session.execute(q % kw))


def history_size_full(session, metric, interval, suite=None):
    """return recent size history of `metric`, over the past `interval`

    `interval` must a be a valid Postgre time interval, see
    http://www.postgresql.org/docs/9.1/static/functions-datetime.html

    """
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('hour', timestamp)",
                             suite=suite)


def history_size_daily(session, metric, interval, suite=None):
    """like `history_size_full`, but taking daily samples"""
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('day', timestamp)",
                             suite=suite)


def history_size_weekly(session, metric, interval, suite=None):
    """like `history_size_full`, but taking weekly samples"""
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('week', timestamp)",
                             suite=suite)


def history_size_monthly(session, metric, interval, suite=None):
    """like `history_size_full`, but taking monthly samples"""
    return _hist_size_sample(session, metric, interval,
                             projection="date_trunc('month', timestamp)",
                             suite=suite)
