/** @odoo-module */
import { registry } from '@web/core/registry';
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, onRendered, onMounted, onWillUnmount } from "@odoo/owl/hooks";
import { Layout } from "@web/search/layout";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
export class StudentAction extends Component {
	setup(){
    	this.action = useService("action");
		this.notificationService = useService("notification");
    	this.rpc = this.env.services.rpc;
		this.students = useState({ data: [] });
        onMounted(()=>{
            this.loadData();
        })
	}
	loadData(){
		this.rpc.query({
        	model: 'oe.school.student',
        	method: 'open_student_form',
        	args:[]
		}).then(function(data){
			console.log('----------- tototototototo data', data)
			this.students.data = data;
    	});
	}
	showNotification() {
        this.notificationService.add(_t("Your changes have been saved successfully."), {
            title: "Success",
            type: "success"
        });
    }
}
StudentAction.template = "siantou_ems_core.student_action";
StudentAction.components = { Layout };
registry.category("actions").add("siantou_ems_core.student_action", StudentAction);
