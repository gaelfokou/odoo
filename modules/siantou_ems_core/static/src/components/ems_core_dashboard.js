/** @odoo-module */

import { registry } from "@web/core/registry"
import { KpiCard } from "./kpi_card/kpi_card"
import { ChartRenderer } from "./chart_renderer/chart_renderer"
import { DoughnutRenderer } from "./doughnut_renderer/doughnut_renderer"
import { loadJS } from "@web/core/assets"
import { useService } from "@web/core/utils/hooks";
const { Component, onWillStart, useRef, onMounted, useState } = owl

export class OwlSalesDashboard extends Component {
    setup() {
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
        })
    }

    async getDatasCount() {
        this.state.cycles.value = await this.orm.searchCount("oe.school.course", [])
        this.state.students.value = await this.orm.searchCount("oe.school.student", [])
        this.state.ecoles.value = await this.orm.searchCount("siantou.ems.core.school", [])
        this.state.campus.value = await this.orm.searchCount("siantou.ems.core.campus", [])
        this.state.teachers.value = await this.orm.searchCount("hr.employee", [["is_teacher", "=", true]])
        this.state.filieres.value = await this.orm.searchCount("siantou.ems.core.field_of_study", [])
        console.log('----------- tototototototo cycles', this.state.cycles);
        console.log('----------- tototototototo students', this.state.students);
        console.log('----------- tototototototo ecoles', this.state.ecoles);
        console.log('----------- tototototototo campus', this.state.campus);
        console.log('----------- tototototototo teachers', this.state.teachers);
        console.log('----------- tototototototo filieres', this.state.filieres);
    }

    async getBarChartDatas() {
        const cycles = await this.orm.searchRead("oe.school.course",[]);
        cycles.forEach( async (cycle) => {
            let studentCount = await this.orm.searchCount("oe.school.student", [["cycle_id", "=", cycle.id]])
            this.state.datas.push({
                name:cycle.name,
                value:studentCount
            })
        });
        console.log('----------- tototototototo datas', this.state.datas);
    }

    async getTearcherDatas() {
        const teacher_vac = await this.orm.searchCount("hr.employee",[["is_teacher", "=", true], ["is_permanent", "=", false]]);
        const teacher_perm = await this.orm.searchCount("hr.employee",[["is_permanent", "=", true], ["is_teacher", "=", true]]);
        this.state.doughTearchers.push({
            name:"Enseignants permanents",
            value:teacher_perm
        })
        this.state.doughTearchers.push({
            name:"Enseignants vacataires",
            value:teacher_vac
        })
        console.log('----------- tototototototo doughTearchers', this.state.doughTearchers);
    }

    async getFiliereDatas() {
        const filieres = await this.orm.searchRead("siantou.ems.core.field_of_study",[]);
        filieres.forEach(async (filiere)=>{
            const classes = await this.orm.searchRead("siantou.ems.core.class",[["field_of_study_id", "=", filiere.id]]);
            let nbre = 0;
            await classes.forEach(async (classe)=>{
                nbre += classe.student_ids.length
            })
            this.state.doughFilieres.push({
                name:filiere.name,
                value:nbre
            })
        });
        console.log('----------- tototototototo doughFilieres', this.state.doughFilieres);
    }

    async getEcoleDatas() {
        const ecoles = await this.orm.searchRead("siantou.ems.core.school",[]);
        ecoles.forEach(async (ecole)=>{
            let nbre = 0
            const filieres = await this.orm.searchRead("siantou.ems.core.field_of_study",[["school_id", "=", ecole.id]]);
            await filieres.forEach(async (filiere)=>{
                const classes = await this.orm.searchRead("siantou.ems.core.class",[["field_of_study_id", "=", filiere.id]]);
                await classes.forEach(async (classe)=>{
                    nbre += classe.student_ids.length
                })
            })
            this.state.doughEcoles.push({
                name:ecole.name,
                value:nbre
            })
        });
        console.log('----------- tototototototo doughEcoles', this.state.doughEcoles);
    }

}

OwlSalesDashboard.template = "owl.OwlSalesDashboard"
OwlSalesDashboard.components = { KpiCard, ChartRenderer, DoughnutRenderer }

registry.category("actions").add("owl.ems_core_dashboard", OwlSalesDashboard)
