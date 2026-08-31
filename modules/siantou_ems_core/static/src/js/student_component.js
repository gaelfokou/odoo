/** @odoo-module */

import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const { Component, whenReady, mount, xml, useRef, useState, onRendered, onMounted, onWillUnmount, onWillStart } = owl;

console.log('Welcome to StudentComponent component');

export class Span extends Component {
	static template = xml`
		<span t-esc="props.text"/>`;
	// static components = { Exemple };
}

export class StudentComponent extends Component {
	setup() {
		super.setup();
    	this.action = useService("action");
		this.notification = useService("notification");
    	this.orm = useService("orm");
        this.state = useState({
            students: [],
        })
        onWillStart(async () => {
            await this.loadData();
        })
	}
	async loadData() {
		let self = this;
        try {
			await self.orm.call('oe.school.student', 'get_students', [[]]).then(function(students) {
				console.log('----------- tototototototo students', students)
				self.state.students = students;
			});
			/* self.orm.search('oe.school.student', [[]]).then(function(students) {
				console.log('----------- tototototototo students', students)
				self.state.students = students;
			}); */
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
	}
	showNotification() {
        this.notification.add(_t('Your changes have been saved successfully'), {
            title: "Success",
            type: "success"
        });
    }
}

StudentComponent.template = "siantou_ems_core.student_component";
StudentComponent.components = { Span }

registry.category("actions").add("siantou_ems_core.student_component", StudentComponent);
