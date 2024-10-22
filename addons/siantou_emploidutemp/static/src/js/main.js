/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
const { Component, mount } = owl;

console.log('Welcome to siantou_emploidutemp module');

export class CustomClientAction extends Component {
	setup() {
		this.videoElement = document.getElementById('videoElement');
		this.canvasElement = document.getElementById('canvasElement');
		this.photoElement = document.getElementById('photoElement');
		this.startButton = document.getElementById('startButton');
		this.captureButton = document.getElementById('captureButton');
		this.stream = null;

		this.loadData();
	}
	loadData() {

		this.startWebcam();

		if(this.startButton !== null) {
			this.startButton.addEventListener('click', this.startWebcam);
		}
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
			if(this.stream !== null) {
				if(this.videoElement !== null) {
					this.videoElement.srcObject = this.stream;
					this.startButton.disabled = true;
					this.captureButton.disabled = false;
					console.log('Successful accessing webcam video streaming');
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
