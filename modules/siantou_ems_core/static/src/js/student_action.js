/** @odoo-module */
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
const { Component, mount, xml, useRef, useState, onRendered, onMounted, onWillUnmount, onWillStart } = owl;

export class Span extends Component {
	static template = xml`
		<span t-esc="props.text"/>`;
	// static components = { Exemple };
}

export class StudentAction extends Component {
	setup() {
		super.setup();
    	this.action = useService("action");
		this.notificationService = useService("notification");
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
		this.orm.call('oe.school.student', 'get_students', [[]]).then(function(data) {
			console.log('----------- tototototototo call data', data)
			self.state.students = data;
    	});
		/* this.orm.search('oe.school.student', [[]]).then(function(data) {
			console.log('----------- tototototototo search data', data)
			self.state.students = data;
    	}); */
	}
	showNotification() {
        this.notificationService.add(_t("Your changes have been saved successfully."), {
            title: "Success",
            type: "success"
        });
    }
}
StudentAction.template = "siantou_ems_core.student_action";
StudentAction.components = { Span }
registry.category("actions").add("siantou_ems_core.student_action", StudentAction);
