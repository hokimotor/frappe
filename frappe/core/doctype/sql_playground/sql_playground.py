# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SQLPlayground(Document):
	pass

@frappe.whitelist()
def execute_query(query):
	if not query.lower().startswith("select") and frappe.session.user != "Administrator":
		frappe.throw("Invalid")

	return frappe.db.sql(query, as_dict=True)
