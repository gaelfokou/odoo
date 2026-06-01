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
                rejected: {
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
                rejected: {
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
        this.state.academic_information.rejected.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "academic_information"], ["status", "=", "rejected"]])
        this.state.academic_information.done.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "academic_information"], ["status", "=", "done"]])
        this.state.exam_score.pending.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "pending"]])
        this.state.exam_score.progress.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "progress"]])
        this.state.exam_score.rejected.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "rejected"]])
        this.state.exam_score.done.value = await this.orm.searchCount("siantou.ems.core.request.track", [["type_request", "=", "exam_score"], ["status", "=", "done"]])
    }

    async viewAcademicInformationPending(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "academic_information"], ["status", "=", "pending"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes informations académiques en attente",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewAcademicInformationProgress(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "academic_information"], ["status", "=", "progress"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes informations académiques en cours",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewAcademicInformationRejected(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "academic_information"], ["status", "=", "rejected"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes informations académiques rejetées",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewAcademicInformationDone(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "academic_information"], ["status", "=", "done"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes informations académiques terminées",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewExamScorePending(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "exam_score"], ["status", "=", "pending"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes notes d'examen en attente",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewExamScoreProgress(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "exam_score"], ["status", "=", "progress"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes notes d'examen en cours",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewExamScoreRejected(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "exam_score"], ["status", "=", "rejected"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes notes d'examen rejetées",
            res_model: "siantou.ems.core.request.track",
            context,
            domain,
            views: [
                [list_view.length > 0 ? list_view[0].res_id : false, "list"],
                [false, "form"],
            ]
        })
    }

    async viewExamScoreDone(){
        let context = { search_default_group_by_status: 1 }
        let domain = [["type_request", "=", "exam_score"], ["status", "=", "done"]]

        let list_view = await this.orm.searchRead("ir.model.data", [["name", "=", "view_request_track_tree"]], ["res_id"])

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Requêtes notes d'examen terminées",
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