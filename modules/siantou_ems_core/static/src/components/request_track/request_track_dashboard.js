/** @odoo-module */

import { registry } from "@web/core/registry"
import { KpiCard } from "./kpi_card/kpi_card"
import { ChartRenderer } from "../chart_renderer/chart_renderer"
const { Component } = owl

export class OwlRequestTrackDashboard extends Component {
    setup(){

    }
}

OwlRequestTrackDashboard.template = "owl.OwlRequestTrackDashboard"
OwlRequestTrackDashboard.components = { KpiCard, ChartRenderer }

registry.category("actions").add("owl.request_track_dashboard", OwlRequestTrackDashboard)