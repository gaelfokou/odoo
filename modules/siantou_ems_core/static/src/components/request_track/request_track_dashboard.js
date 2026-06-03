/** @odoo-module */

import { registry } from "@web/core/registry"
import { KpiCard } from "./kpi_card/kpi_card"
import { ChartRenderer } from "../chart_renderer/chart_renderer"
import { useService } from "@web/core/utils/hooks"
const { Component, useState, onWillStart } = owl

export class OwlRequestTrackDashboard extends Component {
    setup(){
        this.state = useState({
            academic_information: {
                title: 'Informations académiques',
                key: 'academic_information',
                data: {
                    pending: {
                        title: 'En attente',
                        key: 'pending',
                        value: 0,
                    },
                    progress: {
                        title: 'En cours',
                        key: 'progress',
                        value: 0,
                    },
                    rejected: {
                        title: 'Rejeté',
                        key: 'rejected',
                        value: 0,
                    },
                    done: {
                        title: 'Traité',
                        key: 'done',
                        value: 0,
                    }
                }
            },
            exam_score: {
                title: 'Notes d\'examen',
                key: 'exam_score',
                data: {
                    pending: {
                        title: 'En attente',
                        key: 'pending',
                        value: 0,
                    },
                    progress: {
                        title: 'En cours',
                        key: 'progress',
                        value: 0,
                    },
                    rejected: {
                        title: 'Rejeté',
                        key: 'rejected',
                        value: 0,
                    },
                    done: {
                        title: 'Traité',
                        key: 'done',
                        value: 0,
                    }
                }
            }
        })

        this.orm = useService("orm")
        this.actionService = useService("action")

        onWillStart(async ()=>{
            await this.getRequestTracks()
        })
    }

    async getRequestTracks(){
        let self = this
        Object.keys(self.state).forEach((key_type_request) => {
            Object.keys(self.state[key_type_request].data).forEach(async (key_status) => {
                console.log(`${key_type_request} - ${key_status} : ${self.state[key_type_request].data[key_status]}`)
                self.state[key_type_request].data[key_status].value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", key_type_request], ["status", "=", key_status]])
            });
        });
    }

    async viewRequestTracks(type_request, status){
        console.log(`${type_request} - ${status}`)
        // let context = {group_by: ['status']}
        let context = {search_default_group_by_status: 1}
        let domain = [["type_request", "=", type_request], ["status", "=", status]]
        let title_request = ''
        if (type_request == 'academic_information') {
            title_request = 'Requêtes informations académiques'
        } else if (type_request == 'exam_score') {
            title_request = 'Requêtes notes d\'examen'
        }
        let title_status = ''
        if (status == 'pending') {
            title_status = 'en attente'
        } else if (status == 'progress') {
            title_status = 'en cours'
        } else if (status == 'rejected') {
            title_status = 'rejetées'
        } else if (status == 'done') {
            title_status = 'traitées'
        }
        let name = `${title_request} ${title_status}`
        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }
}

OwlRequestTrackDashboard.template = "owl.OwlRequestTrackDashboard"
OwlRequestTrackDashboard.components = { KpiCard, ChartRenderer }

registry.category("actions").add("owl.request_track_dashboard", OwlRequestTrackDashboard)