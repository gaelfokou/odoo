/** @odoo-module */

import { registry } from "@web/core/registry";
import { KpiCard } from "./kpi_card/kpi_card";
import { ChartRenderer } from "./chart_renderer/chart_renderer";
import { DoughnutRenderer } from "./doughnut_renderer/doughnut_renderer";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
const { Component, onWillStart, useRef, onMounted, useState } = owl;

export class OwlSalesDashboard extends Component {
    setup() {
        this.state = useState({
            year: {
                value: 0
            },
            cycles: {
                value: 0
            },
            students: {
                value: 0
            },
            ecoles: {
                value: 0
            },
            campus: {
                value: 0
            },
            teachers: {
                value: 0
            },
            filieres: {
                value: 0
            },
            years: [],
            datas: [],
            doughTearchers: [],
            doughFilieres: [],
            doughEcoles: [],
            userData: null,
            groupData: null
        })

        this.orm = useService("orm")
        this.user = useService("user")
        this.notification = useService("notification")

        onWillStart(async () => {
            let self = this;
            setTimeout(async function() {
                const has_group_dashboard_admin = await self.user.hasGroup("siantou_ems_core.group_dashboard_admin")
                console.log("User has_group_dashboard_admin :", has_group_dashboard_admin);
                await self.checkGroup();
                await self.loadYears();
            }, 2500)
        })

        onMounted(async () => {
    		let self = this;
            setTimeout(async function() {
                await self.loadAllData();
            }, 2500)
        })
    }

    async loadYears() {
		let self = this;
        try {
			await self.orm.call('siantou.ems.core.year', 'get_years', [parseInt(self.state.year.value)]).then(async function(years) {
                self.state.years = years;
				console.log('----------- tototototototo years', years);
                await years.forEach(async (year) => {
                    if (year.is_active) {
                        self.state.year.value = year.id;
                        console.log('----------- tototototototo year', year.id);
                    }
                })
			});
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
	}

    async checkGroup() {
		let self = this;
        try {
            const userId = session.uid;
            console.log("User Id :", userId);
            const userData = await self.orm.read("res.users", [userId])
            console.log("User Details :", userData);
            if (userData.length > 0) {
                self.state.userData = userData[0];
            }
            const groupData = await self.orm.searchRead("res.groups", [["name", "=", "Tableau de bord - admin"]])
            console.log("Group Details :", groupData);
            if (groupData.length > 0) {
                self.state.groupData = groupData[0];
            }
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
	}

    async loadAllData() {
		let self = this;
        try {
            await self.orm.call('hr.employee', 'get_user_group').then(async function(group) {
                if (group.has_group_dashboard_admin) {
                    await Promise.all([
                        self.getDatasCount(),
                        self.getBarChartDatas(),
                        self.getTearcherDatas(),
                        self.getFiliereDatas(),
                        self.getEcoleDatas()
                    ]);
                }
                console.log('----------- tototototototo group', group);
            })
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
	}

    async onChangeYear() {
		let self = this;
        try {
            await self.loadYears();
            await self.loadAllData();
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
    }

    async getDatasCount() {
		let self = this;
        try {
            const [classes, cycleCount, ecoleCount, campusCount, teacherCount, filiereCount] = await Promise.all([
                self.orm.searchRead("siantou.ems.core.class", [["year_id", "=", parseInt(self.state.year.value)]]),
                self.orm.searchCount("oe.school.course", []),
                self.orm.searchCount("siantou.ems.core.school", []),
                self.orm.searchCount("siantou.ems.core.campus", []),
                self.orm.searchCount("hr.employee", [["is_teacher", "=", true]]),
                self.orm.searchCount("siantou.ems.core.field_of_study", [])
            ]);
            let studentCount = 0;
            await classes.forEach(async (classe) => {
                studentCount += classe.number_of_student;
            })
            self.state.students.value = studentCount;
            self.state.cycles.value = cycleCount;
            self.state.ecoles.value = ecoleCount;
            self.state.campus.value = campusCount;
            self.state.teachers.value = teacherCount;
            self.state.filieres.value = filiereCount;
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
    }

    async getBarChartDatas() {
		let self = this;
        try {
            const cycles = await this.orm.searchRead("oe.school.course", [])
            await cycles.forEach(async (cycle) => {
                let studentCount = await this.orm.searchCount("oe.school.student", [["cycle_id", "=", cycle.id]])
                this.state.datas.push({
                    name:cycle.name,
                    value:studentCount
                })
            })
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
    }

    async getTearcherDatas() {
		let self = this;
        try {
            // const teacher_vac = await self.orm.searchCount("hr.employee", [["is_teacher", "=", true], ["is_permanent", "=", false]])
            // const teacher_perm = await self.orm.searchCount("hr.employee", [["is_teacher", "=", true], ["is_permanent", "=", true]])
            const [teacher_vac, teacher_perm] = await Promise.all([
                self.orm.searchCount("hr.employee", [["is_teacher", "=", true], ["is_permanent", "=", false]]),
                self.orm.searchCount("hr.employee", [["is_teacher", "=", true], ["is_permanent", "=", true]])
            ]);
            self.state.doughTearchers.push({
                name:"Enseignants vacataires",
                value:teacher_vac
            })
            self.state.doughTearchers.push({
                name:"Enseignants permanents",
                value:teacher_perm
            })
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
    }

    async getFiliereDatas() {
		let self = this;
        try {
            const filieres = await this.orm.searchRead("siantou.ems.core.field_of_study", [])
            await filieres.forEach(async (filiere) => {
                const classes = await this.orm.searchRead("siantou.ems.core.class", [["field_of_study_id", "=", filiere.id]])
                let nbre = 0;
                await classes.forEach(async (classe) => {
                    nbre += classe.student_ids.length;
                })
                this.state.doughFilieres.push({
                    name:filiere.name,
                    value:nbre
                })
            })
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
    }

    async getEcoleDatas() {
		let self = this;
        try {
            const ecoles = await this.orm.searchRead("siantou.ems.core.school", [])
            await ecoles.forEach(async (ecole) => {
                let nbre = 0;
                const filieres = await this.orm.searchRead("siantou.ems.core.field_of_study", [["school_id", "=", ecole.id]])
                await filieres.forEach(async (filiere) => {
                    const classes = await this.orm.searchRead("siantou.ems.core.class", [["field_of_study_id", "=", filiere.id]])
                    await classes.forEach(async (classe) => {
                        nbre += classe.student_ids.length;
                    })
                })
                this.state.doughEcoles.push({
                    name:ecole.name,
                    value:nbre
                })
            })
        } catch(error) {
            console.log("Erreur lors du chargement des données :", error);
            self.notification.add(`Erreur lors du chargement des données : ${ error.message }`, { type: "danger" });
        }
    }
}

OwlSalesDashboard.template = "owl.EmsCoreDashboard";
OwlSalesDashboard.components = { KpiCard, ChartRenderer, DoughnutRenderer };

registry.category("actions").add("owl.ems_core_dashboard", OwlSalesDashboard);
