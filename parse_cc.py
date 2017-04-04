from bs4 import BeautifulSoup
from HTMLParser import HTMLParser
import os
import re


def html_unicode_to_unicode(string):
	htmlparser = HTMLParser()
	return htmlparser.unescape(string)


def load_files_list():
	"""
	loads file with paths from the source dir
	prioritizes txt over html
	"""
	root = '../legalcode/'
	lics = dict()
	for i in os.listdir(root):
		if i.endswith('.html'):
			lics[i[:-5]] = root + i
		elif i.endswith('.txt') and (i[:-4] not in lics):
			lics[i[:-4]] = root + i
	return lics


def get_skeleton_lic_data(text, key, fullname=None, rule=None, title=None):
	"""
	returns skeleton data used in :parse_license_list
	TODO: name deed_license (3) or p align center (2)
	TODO: homepage https://creativecommons.org/licenses/by-nc/3.0/legalcode.eg
	TODO: category maybe manually
	"""
	return {
		'text': text,
		'rule': rule,
		'shortname': key.upper(),
		'title': title,
		'owner': 'Creative Commons',
		'category': 'Copyleft Limited',
		'homepage_url': None,
		'text_url': None,
		'spdx_license_key': key.upper(),
		'fullname': title if fullname is None else fullname
	}


def parse_license_html(path):
	"""
	parses the license html and returns the componenets
	"""
	data = open(path, 'r').read()
	# extract notice
	notice_reg = r'<!-- BREAKOUT FOR CC NOTICE.*?END CC NOTICE -->'
	searchObj = re.search(notice_reg, data, re.IGNORECASE | re.DOTALL | re.MULTILINE)
	notice = None
	if searchObj:
		notice = searchObj.group()
		data = data.replace(notice, '')
		soup = BeautifulSoup(notice, 'html.parser')
		notice = soup.get_text()
	# get license
	soup = BeautifulSoup(data, 'html.parser')
	text = soup.get_text()
	# title
	title = soup.find('title')
	if title is None:
		print ('ERROR: None Title: ', path)
		title = path
	else:
		title = title.getText().strip(' \t\r\n')
	# fullname
	# no try..catch here as this should work for a CC license
	fullname = soup.find('div', {"id": "deed-license"})
	if fullname is None:
		fullname = soup.find('div', {'id': 'deed'}).find('p')
		fullname = fullname.getText()
	else:
		fullname = fullname.getText()
	fullname = fullname.strip(' \t\r\n')
	# return
	return {
		'notice': notice,
		'text': text,
		'title': title,
		'fullname': fullname
	}


def make_lic_url(key):
	"""
	makes the license url given the key
	THIS information is not available in the source files
	All licenses have versions
	https://creativecommons.org/licenses/by-nc-nd/2.1/ca/legalcode.fr
	"""
	key = key[3:]  # cc-
	# Regexes
	regex_normal = r'^([a-z\-]*)\-([\d\.]*)$' # by-nc-sa-3.0
	regex_transl = r'^([a-z\-]*)\-([\d\.]*)\-([a-z]*)$' # by-nc-sa-3.0-cr
	regex_local_transl = r'^([a-z\-]*)\-([\d\.]*)\-([a-z]*)\-([a-z]*)$' # by-nc-3.0-ch-de
	regex_local_transl_2 = r'^([a-z\-]*)\-([\d\.]*)\-([a-z]*)\-([a-z\-]*)$' # by-3.0-rs-sr-Cyrl

	url = None
	if re.match(regex_normal, key, re.I):
		mo = re.match(regex_normal, key, re.I)
		url = 'https://creativecommons.org/licenses/%s/%s/legalcode' % (mo.group(1), mo.group(2))
	elif re.match(regex_transl, key, re.I):
		mo = re.match(regex_transl, key, re.I)
		url = 'https://creativecommons.org/licenses/%s/%s/legalcode.%s' % (mo.group(1), mo.group(2), mo.group(3))
	elif re.match(regex_local_transl, key, re.I):
		mo = re.match(regex_local_transl, key, re.I)
		url = 'https://creativecommons.org/licenses/%s/%s/%s/legalcode.%s' % (mo.group(1), mo.group(2), mo.group(3), mo.group(4))
	elif re.match(regex_local_transl_2, key, re.I):
		mo = re.match(regex_local_transl_2, key, re.I)
		url = 'https://creativecommons.org/licenses/%s/%s/%s/legalcode.%s' % (mo.group(1), mo.group(2), mo.group(3), mo.group(4))
	else:
		print ('ERROR: License url => ', key)
	return url


def parse_license_list(lics):
	"""
	get lics list and parse it and return data object
	"""
	result = dict()
	for i in lics:
		path = lics[i]
		newName = 'cc-' + i.replace('_', '-')
		if path.endswith('.txt'):
			print ('ERROR: Shouldn\'t be possible')
			lic_data = open(path, 'r').read()
			title = lic_data[:lic_data.find('\n')+1]
			result[newName] = get_skeleton_lic_data(lic_data, newName, title=title)
		elif path.endswith('.html'):
			comps = parse_license_html(path)
			result[newName] = get_skeleton_lic_data(
				comps['text'], newName, rule=comps['notice'], title=comps['title'],
				fullname=comps['fullname']
			)
			result[newName]['text_url'] = make_lic_url(newName)
			if result[newName]['text_url']:
				result[newName]['homepage_url'] = re.sub(r'legalcode.*', '', result[newName]['text_url'])
	return result


def write_result(scanResult):
	"""
	writes result back to directories
	"""
	# write new
	for i in scanResult:
		print (html_unicode_to_unicode( scanResult[i]['fullname'] ), scanResult[i]['homepage_url'])



if __name__ == '__main__':
	print ('Script might take time...')
	lics = load_files_list()
	res = parse_license_list(lics)
	print (len(res))
	write_result(res)
