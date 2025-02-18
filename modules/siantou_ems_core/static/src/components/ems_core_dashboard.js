/** @odoo-module */

import { registry } from "@web/core/registry"
import { KpiCard } from "./kpi_card/kpi_card"
import { ChartRenderer } from "./chart_renderer/chart_renderer"
import { DoughnutRenderer } from "./doughnut_renderer/doughnut_renderer"
import { loadJS } from "@web/core/assets"
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useRef, onMounted, useState } = owl

export class OwlSalesDashboard extends Component {
    setup(){
        this.state = useState({
            cycles:{
                value:0
            },
            students:{
                value:0
            },
            ecoles:{
                value:0
            },
            campus:{
                value:0
            },
            teachers:{
                value:0
            },
            filieres:{
                value:0
            },
            datas:[],
            doughTearchers:[],
            doughFilieres:[],
            doughEcoles:[],
        })
        this.orm = useService("orm")

        onWillStart(async ()=>{
            await this.getDatasCount()
            await this.getBarChartDatas()
            await this.getTearcherDatas()
            await this.getFiliereDatas()
            await this.getEcoleDatas()
            // console.log(this.state)
        })
    }

    async getDatasCount(){
        this.state.cycles.value = await this.orm.searchCount("oe.school.course", [])
        this.state.students.value = await this.orm.searchCount("oe.school.student", [])
        this.state.ecoles.value = await this.orm.searchCount("siantou.ems.core.school", [])
        this.state.campus.value = await this.orm.searchCount("siantou.ems.core.campus", [])
        this.state.teachers.value = await this.orm.searchCount("hr.employee", [["is_teacher","=",true]])
        this.state.filieres.value = await this.orm.searchCount("siantou.ems.core.field_of_study", [])
    }

    async getBarChartDatas(){
        const cycles = await this.orm.searchRead("oe.school.course",[]);
        cycles.forEach( async (cycle) => {
            let studentCount = await this.orm.searchCount("oe.school.student", [["cycle_id","=",cycle.id]])
            this.state.datas.push({
                name:cycle.name,
                value:studentCount
            })
        });
    }

    async getTearcherDatas(){
        const teacher_vac = await this.orm.searchCount("hr.employee",[["is_teacher","=",true], ["is_permanent","=",false]]);
        const teacher_perm = await this.orm.searchCount("hr.employee",[["is_permanent","=",true], ["is_teacher","=",true]]);
        this.state.doughTearchers.push({
            name:"Enseignants permanents",
            value:teacher_perm
        })
        this.state.doughTearchers.push({
            name:"Enseignants vacataires",
            value:teacher_vac
        })
    }

    async getFiliereDatas(){
        const filieres = await this.orm.searchRead("siantou.ems.core.field_of_study",[]);
        filieres.forEach(async (filiere)=>{
            this.state.doughFilieres.push({
                name:filiere.name,
                value:filiere.student_ids.length
            })
        })
        console.log(this.state.doughFilieres)
    }

    async getEcoleDatas(){
        const ecoles = await this.orm.searchRead("siantou.ems.core.school",[]);
        ecoles.forEach(async (ecole)=>{
            let nbre = 0
            const filieres = await this.orm.searchRead("siantou.ems.core.field_of_study",[["school_id","=",ecole.id]]);
            filieres.forEach(async (filiere)=>{
                nbre += filiere.student_ids.length
            })

            this.state.doughEcoles.push({
                name:ecole.name,
                value:nbre
            })
        })
        console.log(this.state.doughEcoles)
    }

}

OwlSalesDashboard.template = "owl.OwlSalesDashboard"
OwlSalesDashboard.components = { KpiCard, ChartRenderer, DoughnutRenderer }

registry.category("actions").add("owl.ems_core_dashboard", OwlSalesDashboard)