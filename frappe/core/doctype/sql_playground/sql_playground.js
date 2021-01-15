// Copyright (c) 2020, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('SQL Playground', {
	refresh: function(frm) {
		cur_frm.disable_save();
	},

	run:function(){
		if(cur_frm.doc.sql_query){
			frappe.call({
				method: "frappe.core.doctype.sql_playground.sql_playground.execute_query",
				args: {
					query: cur_frm.doc.sql_query
				},
				callback: (res)=>{ 
					if(res.message && res.message.length > 0){
						let fields = Object.keys(res.message[0]);
						let table = $.parseHTML(`<table class="table table-bordered"></table>`);
						table = $(table);
						
						let thead = "<tr>";
						fields.forEach(field => {
							thead += `<td><b>${field}</b></td>`
						});
						thead += "</tr>";
						table.append(thead);

						res.message.forEach(row => {
							let r = "<tr>";
							fields.forEach(field => {
								r += `<td>${row[field] || ""}</td>`
							});
							r += "</tr>";
							table.append(r);
						});

						cur_frm.fields_dict.result_html.$wrapper.html("");
						cur_frm.fields_dict.result_html.$wrapper.append(table);
					}
				}
			})
		}
	}
});
