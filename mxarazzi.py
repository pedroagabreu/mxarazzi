#!/usr/bin/env python3

import sys
import smtplib
import sqlite3
import dns.resolver
import socket
import os

from optparse import OptionParser

mxdb = './mxdb.db'

def check_mx(d):
	"""Return the MX records for a domain"""
	try:
		q = dns.resolver.query(d, 'MX')
	except:
		print('Error resolving domain.')
		return
	result = []
	for r in q:
		result.append((str(r.exchange), int(r.preference)))
	return result

def check_banner(mx):
	"""Return the banner of an MX record"""
	# XXX need to catch exceptions such as timeouts or
	# conn refused
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((mx, 25))
	data = s.recv(1024)
	s.close()
	print(data[0:-2].decode())

def update_banners():
	"""Update the banners of all MX records in the database"""
	c = conn.cursor()
	c.execute('select mx from mxrecords')
	r = c.fetchall()
	for n in r:
		check_banner(n[0])
	c.close()

def add_mx(mx, p, d):
	"""Add an MX record to a domain"""
	c = conn.cursor()
	try:
		c.execute('insert into mxrecords(mx) values (?)', (mx,))
		conn.commit()
	except sqlite3.IntegrityError:
		# mx already in the database, no problem.
		pass
	c.execute('select id from mxrecords where mx=?', (mx,))
	r = c.fetchone()
	c.execute('insert into domains(domain,mx,pref) values (?,?,?)',
	 (str(d,),int(r[0]),int(p,)))
	conn.commit()
	print('MX record ' + mx + ' added to domain ' + d)
	c.close()

def check_domain(d):
	"""Check if a domain exists in the database"""
	c = conn.cursor()
	c.execute('select id from domains where domain=?', (d,))
	r = c.fetchone()
	return r

def add_domain(d):
	"""Add a new domain to the database"""
	r = check_domain(d)
	if r:
		print('Domain ' + d + ' already in the database, skipping.')
		return
	r = check_mx(d)
	if r:
		i = len(r)
		while i > 0:
			add_mx(r[i-1][0], r[i-1][1], d)
			i = i - 1
	else:
		print('No MX records found, skipping.')

def delete_domain(d):
	"""Delete a domain from the database"""
	r = check_domain(d)
	if r:
		c = conn.cursor()
		c.execute('delete from domains where domain=?', (d,))
		conn.commit()
		print('Domain ' + d + ' deleted from the database.')
		c.close()
	else:
		print('Domain ' + d + ' not found in the database.')

def list_domains():
	"""List all domains currently in the database"""
	c = conn.cursor()
	c.execute('select distinct domain from domains')
	r = c.fetchall()
	for d in r:
		print(d[0])
	c.close()

parser = OptionParser(usage="""Usage: %prog [options] arg""")
parser.add_option('-a', '--add-domain',
	type='string', action='store', dest='newdomain',
	metavar='DOMAIN',
	help="""domain name to add to database""")
parser.add_option('-d', '--delete-domain',
	type='string', action='store', dest='olddomain',
	metavar='DOMAIN',
	help="""domain name to delete from database""")
parser.add_option('-u', '--update-banners',
	action='store_true', dest='update', default=False,
	help="""update all MX banners""")
parser.add_option('-l', '--list-domains',
	action='store_true', dest='listd', default=False,
	help="""list domains currently in database""")
opts, args = parser.parse_args()

# XXX do a backup of the database here if it exists

# initialize database
conn = sqlite3.connect(mxdb)
createdb = '''
	create table if not exists domains (
		id integer primary key autoincrement,
		domain text,
		mx integer,
		pref integer,
		foreign key (mx) references mxrecords(id)
	);
	create table if not exists mxrecords (
		id integer primary key autoincrement,
		mx text unique,
		banner text
	);
'''
c = conn.cursor()
c.executescript(createdb)
conn.commit()
c.close()

if opts.listd:
	list_domains()
elif opts.update:
	update_banners()
elif opts.newdomain:
	add_domain(opts.newdomain)
elif opts.olddomain:
	delete_domain(opts.olddomain)
else:
	parser.print_help()
	sys.exit(1)

sys.exit(0)

