/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, onRendered, onMounted, onWillUnmount } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
const { Component, mount } = owl;

const delay = ms => new Promise(res => setTimeout(res, ms));

var videoElement = document.getElementById('siantou_emploidutemp.video_element');
var canvasElement = document.getElementById('siantou_emploidutemp.canvas_element');
var photoElement = document.getElementById('siantou_emploidutemp.photo_element');
var startButton = document.getElementById('siantou_emploidutemp.start_button');
var captureButton = document.getElementById('siantou_emploidutemp.capture_button');
var stream = null;

console.log('Welcome to siantou_emploidutemp module');

export class CustomClientAction extends Component {
	setup() {
		this.state = useState({
			count: 0,
		});
		onRendered(async () => {
			if(!videoElement || !canvasElement || !photoElement || !startButton || !captureButton) {
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
		if(startButton) {
			startButton.disabled = false;
			startButton.addEventListener('click', this.startWebcam);
			console.log('Add event listener on component');
		}
		console.log('Component mounted');
	}
	removeEventElement() {
		if(startButton) {
			startButton.removeEventListener('click', this.startWebcam);
			console.log('Remove event listener on component');
		}
		console.log('Component unmounted');
	}
	getElements() {
		videoElement = document.getElementById('siantou_emploidutemp.video_element');
		canvasElement = document.getElementById('siantou_emploidutemp.canvas_element');
		photoElement = document.getElementById('siantou_emploidutemp.photo_element');
		startButton = document.getElementById('siantou_emploidutemp.start_button');
		captureButton = document.getElementById('siantou_emploidutemp.capture_button');
		stream = null;
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
			stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
			if(stream) {
				if(videoElement) {
					videoElement.srcObject = stream;
					startButton.disabled = true;
					captureButton.disabled = false;
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
