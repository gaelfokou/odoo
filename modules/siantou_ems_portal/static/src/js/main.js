/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const { Component, whenReady, mount, xml, useRef, useState, onRendered, onMounted, onWillUnmount, onWillStart } = owl;

console.log('Welcome to PrintTimetableComponent component');

var siantou_ems_portal_print_timetable_container = null;

const delay = ms => new Promise(res => setTimeout(res, ms));


class PrintTimetableComponent extends Component {
	setup() {
		// this.orm = useService('orm');
    	// this.rpc = this.env.services.rpc;
	}
	printTimetable() {
		/* this.orm.call(
			'siantou.ems.timetable.timetable',
			'action_timetable_print',
			[]
		); */
		/* this.rpc.query({
        	model: 'siantou.ems.timetable.timetable',
        	method: 'action_timetable_print',
        	args: []
		}).then(function(data) {
			console.log(data)
    	}); */

		console.log('Successful starting print timetable');
	}
	static template = xml`<button id="siantou_ems_portal.print_timetable_element" class="btn btn-primary" t-on-click="printTimetable">Impression de l'emploi du temps</button>`;
}

registry.category('actions').add('siantou_ems_portal.print_timetable', PrintTimetableComponent)

export function getElements() {
	whenReady().then(() => {
		siantou_ems_portal_print_timetable_container = document.getElementById('siantou_ems_portal_print_timetable_container');

		if(siantou_ems_portal_print_timetable_container) {
			mount(PrintTimetableComponent, siantou_ems_portal_print_timetable_container);
		}
	});

	console.log('Get all elements');
}

if(!siantou_ems_portal_print_timetable_container) {
	delay(2000);
	getElements();
}
