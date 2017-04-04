from bs4 import BeautifulSoup
from html.parser import HTMLParser
import os
import re


##############
### VARIABLES

YML = """key: %s
short_name: %s
name: >-
    %s

category: %s
owner: %s
homepage_url: %s
spdx_license_key: %s
text_urls:
    - %s
"""

RULE_YML = """licenses:
    - %s
"""


#############
### CODE

def html_unicode_to_unicode(string):
	htmlparser = HTMLParser()
	return htmlparser.unescape(string)


def load_files_list(limit=5):
	"""
	loads file with paths from the source dir
	prioritizes txt over html
	"""
	root = '../legalcode/'
	# for same order
	files = []
	for i in os.listdir(root):
		files.append(i)
	files = sorted(files)
	# next steps
	lics = dict()
	for i in files:
		if i.endswith('.html'):
			lics[i[:-5]] = root + i
		elif i.endswith('.txt') and (i[:-4] not in lics):
			lics[i[:-4]] = root + i
		limit -= 1
		if limit == 0:
			break
	return lics


def get_skeleton_lic_data(text, key, fullname=None, rule=None, title=None):
	"""
	returns skeleton data used in :parse_license_list
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
	body = soup.find('body').find('div')  # first div after body
	# see cc 2.5 example
	text = body.getText()
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
		fullname = soup.find('div', {'id': 'deed'})
		pc = fullname.find('p', {'align': 'center'})
		if pc is None:
			fullname = fullname.find('h1', {'align': 'center'})
		else:
			fullname = pc
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
				fullname='Creative Commons ' + comps['fullname']
			)
			result[newName]['text_url'] = make_lic_url(newName)
			if result[newName]['text_url']:
				result[newName]['homepage_url'] = re.sub(r'legalcode.*', '', result[newName]['text_url'])
	return result


def write_result(scanResult):
	"""
	writes result back to directories
	"""
	# create dirs
	if not os.path.isdir('licenses'):
		os.mkdir('licenses')
	if not os.path.isdir('rules'):
		os.mkdir('rules')
	# create files
	for i in scanResult:
		d = scanResult[i]
		# write license
		lic_text = scanResult[i]['text']
		fp = open('licenses/' + i + '.LICENSE', 'w', encoding='utf-8')
		fp.write(lic_text)
		fp.close()
		# write yml
		yml_str = YML % (i, d['shortname'], d['fullname'], d['category'], d['owner'],
				d['homepage_url'], d['spdx_license_key'], d['text_url'])
		fp = open('licenses/' + i + '.yml', 'w', encoding='utf-8')
		fp.write(yml_str)
		fp.close()
		# write rule
		if not d['rule']:
			continue
		rule_text = d['rule']
		fp = open('rules/' + i + '.RULE', 'w', encoding='utf-8')
		fp.write(rule_text)
		fp.close()
		# write rule yml
		yml_str = RULE_YML % (i)
		fp = open('rules/' + i + '.yml', 'w', encoding='utf-8')
		fp.write(yml_str)
		fp.close()


if __name__ == '__main__':
	print ('Script might take time...')
	lics = load_files_list()
	res = parse_license_list(lics)
	print (len(res))
	write_result(res)
