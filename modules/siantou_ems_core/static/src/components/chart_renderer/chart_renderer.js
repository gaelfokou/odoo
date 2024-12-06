/** @odoo-module */

import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
const { Component, onWillStart, useRef, onMounted } = owl

export class ChartRenderer extends Component {
    setup(){
        this.chartRef = useRef("chart")
        onWillStart(async ()=>{
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
        })

        onMounted(()=>this.renderChart())
    }

    renderChart(){
        new Chart(this.chartRef.el,
        {
          type: this.props.type,
          data: {
            labels: this.props.datas.map(d=>d.name),
              datasets: [
                {
                  label: 'Données',
                  data: this.props.datas.map(d=>d.value),
                  borderWidth: 1
                }
              ]
          },
          options: {
            scales: {
              y: {
                beginAtZero: true
              }
            }
          },
        }
      );
    }
}

ChartRenderer.template = "owl.ChartRenderer"