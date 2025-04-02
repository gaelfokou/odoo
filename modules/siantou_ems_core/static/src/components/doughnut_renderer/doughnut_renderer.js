/** @odoo-module */

import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
const { Component, onWillStart, useRef, onMounted } = owl

export class DoughnutRenderer extends Component {
    setup() {
      this.doughRef = useRef("doughRef")
      onWillStart(async ()=>{
          await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
      })
      onMounted(()=>this.renderChart())
    }

    renderChart() {
        new Chart(this.doughRef.el,
          {
            type: this.props.type,
            data: {
              labels: this.props.datas.map(d=>d.name),
                datasets: [
                  {
                    label: 'Effectif',
                    data: this.props.datas.map(d=>d.value),
                    hoverOffset: 4
                  }
                ]
            },
            options: {
              responsive: true,
              plugins: {
                legend: {
                  position: 'bottom',
                },
                title: {
                  display: false,
                  text: this.props.title,
                  position: 'bottom',
                }
              }
            },
          }
      );
    }
}

DoughnutRenderer.template = "owl.DoughnutRenderer"