# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
from __future__ import unicode_literals

import pdfkit, os, frappe
from distutils.version import LooseVersion
from frappe.utils import scrub_urls, get_wkhtmltopdf_version
from frappe import _
import six, re, io
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileReader, PdfFileWriter

def get_pdf(html, options=None, output=None):
	html = scrub_urls(html)
	html, options = prepare_options(html, options)

	options.update({
		"disable-javascript": "",
		"disable-local-file-access": "",
		'dpi': '500',
		'margin-top': '2mm',
		'margin-bottom': '0mm',
		'margin-left': '5mm',
		'margin-right': '5mm',
		# 'page-width': 150,
		# 'page-height': 150
	})

	filedata = ''
	if LooseVersion(get_wkhtmltopdf_version()) > LooseVersion('0.12.3'):
		options.update({"disable-smart-shrinking": ""})

	try:
		# Set filename property to false, so no file is actually created
		filedata = pdfkit.from_string(html, False, options=options or {})

		# https://pythonhosted.org/PyPDF2/PdfFileReader.html
		# create in-memory binary streams from filedata and create a PdfFileReader object
		reader = PdfFileReader(io.BytesIO(filedata))

	except IOError as e:
		if ("ContentNotFoundError" in e.message
			or "ContentOperationNotPermittedError" in e.message
			or "UnknownContentError" in e.message
			or "RemoteHostClosedError" in e.message):

			# allow pdfs with missing images if file got created
			if filedata:
				if output: # output is a PdfFileWriter object
					output.appendPagesFromReader(reader)

			else:
				frappe.throw(_("PDF generation failed because of broken image links"))
		else:
			raise

	if "password" in options:
		password = options["password"]
		if six.PY2:
			password = frappe.safe_encode(password)

	if output:
		output.appendPagesFromReader(reader)
		return output

	writer = PdfFileWriter()
	writer.appendPagesFromReader(reader)

	if "password" in options:
		writer.encrypt(password)

	filedata = get_file_data_from_writer(writer)

	return filedata

def get_file_data_from_writer(writer_obj):

	# https://docs.python.org/3/library/io.html
	stream = io.BytesIO()
	writer_obj.write(stream)

	# Change the stream position to start of the stream
	stream.seek(0)

	# Read up to size bytes from the object and return them
	return stream.read()


def prepare_options(html, options):
	if not options:
		options = {}

	options.update({
		'print-media-type': None,
		'background': None,
		'images': None,
		'quiet': None,
		# 'no-outline': None,
		'encoding': "UTF-8",
		#'load-error-handling': 'ignore'
	})

	if not options.get("margin-right"):
		options['margin-right'] = '10mm'

	if not options.get("margin-left"):
		options['margin-left'] = '10mm'

	html, html_options = read_options_from_html(html)
	options.update(html_options or {})

	# cookies
	if frappe.session and frappe.session.sid:
		options['cookie'] = [('sid', '{0}'.format(frappe.session.sid))]

	# page size
	if options.get("width") and options.get("min-height"):
		options['page-width'] = options.get("width")
		options['page-height'] = options.get("min-height")
		del options["width"]
		del options["min-height"]

	if not options.get("page-size"):
		options['page-size'] = frappe.db.get_single_value("Print Settings", "pdf_page_size") or "A4"

	return html, options

def read_options_from_html(html):
	options = {}
	soup = BeautifulSoup(html, "html5lib")

	options.update(prepare_header_footer(soup))

	toggle_visible_pdf(soup)

	# use regex instead of soup-parser
	for attr in ("margin-top", "margin-bottom", "margin-left", "margin-right", "page-size", "header-spacing", "width", "min-height"):
		try:
			pattern = re.compile(r"(\.print-format)([\S|\s][^}]*?)(" + str(attr) + r":)(.+)(mm;)")
			match = pattern.findall(html)
			if match:
				options[attr] = str(match[-1][3]).strip()
		except:
			pass

	return soup.prettify(), options

def prepare_header_footer(soup):
	options = {}

	head = soup.find("head").contents
	styles = soup.find_all("style")

	bootstrap = frappe.read_file(os.path.join(frappe.local.sites_path, "assets/frappe/css/bootstrap.css"))
	fontawesome = frappe.read_file(os.path.join(frappe.local.sites_path, "assets/frappe/css/font-awesome.css"))

	# extract header and footer
	for html_id in ("header-html", "footer-html"):
		content = soup.find(id=html_id)
		if content:
			# there could be multiple instances of header-html/footer-html
			for tag in soup.find_all(id=html_id):
				tag.extract()

			toggle_visible_pdf(content)
			html = frappe.render_template("templates/print_formats/pdf_header_footer.html", {
				"head": head,
				"styles": styles,
				"content": content,
				"html_id": html_id,
				"bootstrap": bootstrap,
				"fontawesome": fontawesome
			})

			# create temp file
			fname = os.path.join("/tmp", "frappe-pdf-{0}.html".format(frappe.generate_hash()))
			with open(fname, "wb") as f:
				f.write(html.encode("utf-8"))

			# {"header-html": "/tmp/frappe-pdf-random.html"}
			options[html_id] = fname
		else:
			if html_id == "header-html":
				options["margin-top"] = "10mm"
			elif html_id == "footer-html":
				options["margin-bottom"] = "10mm"

	return options

def cleanup(fname, options):
	if os.path.exists(fname):
		os.remove(fname)

	for key in ("header-html", "footer-html"):
		if options.get(key) and os.path.exists(options[key]):
			os.remove(options[key])

def toggle_visible_pdf(soup):
	for tag in soup.find_all(attrs={"class": "visible-pdf"}):
		# remove visible-pdf class to unhide
		tag.attrs['class'].remove('visible-pdf')

	for tag in soup.find_all(attrs={"class": "hidden-pdf"}):
		# remove tag from html
		tag.extract()
