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
                pending: {
                    value: 0,
                },
                progress: {
                    value: 0,
                },
                done: {
                    value: 0,
                },
            },
            exam_score: {
                pending: {
                    value: 0,
                },
                progress: {
                    value: 0,
                },
                done: {
                    value: 0,
                },
            },
        })

        this.orm = useService("orm")
        this.actionService = useService("action")

        onWillStart(async ()=>{
            await this.getRequestTracks()
        })
    }

    async getRequestTracks(){
        this.state.academic_information.pending.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "academic_information"], ["status", "=", "pending"]])
        this.state.academic_information.progress.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "academic_information"], ["status", "=", "progress"]])
        this.state.academic_information.done.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "academic_information"], ["status", "=", "done"]])
        this.state.exam_score.pending.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "pending"]])
        this.state.exam_score.progress.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "progress"]])
        this.state.exam_score.done.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "done"]])
    }
}

OwlRequestTrackDashboard.template = "owl.OwlRequestTrackDashboard"
OwlRequestTrackDashboard.components = { KpiCard, ChartRenderer }

registry.category("actions").add("owl.request_track_dashboard", OwlRequestTrackDashboard)