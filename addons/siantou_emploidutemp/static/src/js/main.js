/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, onRendered, onMounted, onWillUnmount } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
const { Component, mount } = owl;

const delay = ms => new Promise(res => setTimeout(res, ms));

console.log('Welcome to siantou_emploidutemp module');

export class CustomClientAction extends Component {
	setup() {
		this.state = useState({
			count: 0,
		});
		onRendered(async () => {
			if(!this.videoElement || !this.canvasElement || !this.photoElement || !this.startButton || !this.captureButton) {
				this.getElements();
				console.log('Count :', this.state.count);
				await delay(5000);
				this.state.count += 1;
			} else {
				this.addEventElement();
			}
			console.log('Component rendered');
		});
		onMounted(() => {
			this.addEventElement();
		});
		onWillUnmount(() => {
			this.removeEventElement();
		});
	}
	addEventElement() {
		if(this.startButton) {
			this.startButton.disabled = false;
			this.startButton.addEventListener('click', this.startWebcam);
			console.log('Add event listener on component');
		}
		console.log('Component mounted');
	}
	removeEventElement() {
		if(this.startButton) {
			this.startButton.removeEventListener('click', this.startWebcam);
			console.log('Remove event listener on component');
		}
		console.log('Component unmounted');
	}
	getElements() {
		this.videoElement = document.getElementById('videoElement');
		this.canvasElement = document.getElementById('canvasElement');
		this.photoElement = document.getElementById('photoElement');
		this.startButton = document.getElementById('startButton');
		this.captureButton = document.getElementById('captureButton');
		this.stream = null;
		console.log('Get all elements');
	}
	async startWebcam() {
		try {
			navigator.mediaDevices.getUserMedia = (
				navigator.mediaDevices.getUserMedia ||
				navigator.mediaDevices.webkitGetUserMedia ||
				navigator.mediaDevices.mozGetUserMedia ||
				navigator.mediaDevices.msGetUserMedia
			);
			this.stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
			if(this.stream) {
				if(this.videoElement) {
					this.videoElement.srcObject = this.stream;
					this.startButton.disabled = true;
					this.captureButton.disabled = false;
					console.log('Successful accessing video streaming');
				} else {
					console.log('Error accessing video');
				}
			} else {
				console.log('Error accessing stream');
			}
		} catch (error) {
			console.log('Error accessing webcam :', error);
		}
	}
}

CustomClientAction.template = 'siantou_emploidutemp.custom_client'

registry.category('actions').add('siantou_emploidutemp.custom_client_action', CustomClientAction)
