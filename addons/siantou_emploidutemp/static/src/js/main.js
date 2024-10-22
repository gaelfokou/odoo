/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, onRendered, onMounted, onWillUnmount } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
const { Component, mount } = owl;

const delay = ms => new Promise(res => setTimeout(res, ms));

var width = 320;
var height = 0;
var streaming = false;

var videoElement = null;
var canvasElement = null;
var photoElement = null;
var startButton = null;
var captureButton = null;
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
				this.addEventElements();
			}
			console.log('Component rendered');
		});
		onMounted(() => {
			this.addEventElements();
			console.log('Component mounted');
		});
		onWillUnmount(() => {
			this.removeEventElements();
			console.log('Component unmounted');
		});
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
	addEventElements() {
		if(startButton) {
			startButton.disabled = false;
			startButton.addEventListener('click', this.startWebcam, false);
			console.log('Add event listener on start button');
		}
		if(videoElement) {
			videoElement.addEventListener('canplay', this.canPlayVideo, false);
			console.log('Add event listener on video element');
		}
		if(captureButton) {
			captureButton.addEventListener('click', this.capturePhoto, false);
			console.log('Add event listener on capture button');
		}
	}
	removeEventElements() {
		if(startButton) {
			startButton.removeEventListener('click', this.startWebcam);
			console.log('Remove event listener on start button');
		}
		if(videoElement) {
			videoElement.removeEventListener('canplay', this.canPlayVideo);
			console.log('Remove event listener on video element');
		}
		if(captureButton) {
			captureButton.removeEventListener('click', this.capturePhoto);
			console.log('Remove event listener on capture button');
		}
	}
	async startWebcam(event) {
		event.preventDefault();
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
	canPlayVideo() {
		if (!streaming) {
			height = videoElement.videoHeight / (videoElement.videoWidth / width);

			if (isNaN(height)) {
				height = width / (4 / 3);
			}

			videoElement.setAttribute('width', width);
			videoElement.setAttribute('height', height);
			canvasElement.setAttribute('width', width);
			canvasElement.setAttribute('height', height);
			streaming = true;
		}
	}
	clearPhoto() {
		var context = canvasElement.getContext('2d');
		context.fillStyle = "#AAA";
		context.fillRect(0, 0, canvasElement.width, canvasElement.height);

		const photoDataUrl = canvasElement.toDataURL('image/png');
		photoElement.setAttribute('src', photoDataUrl);
		/* photoElement.src = photoDataUrl;
		photoElement.style.display = 'block'; */
	}
	capturePhoto() {
		var context = canvasElement.getContext('2d');
		if (width && height) {
			canvasElement.width = width;
			canvasElement.height = height;
			context.drawImage(videoElement, 0, 0, width, height);

			const photoDataUrl = canvasElement.toDataURL('image/png');
			photoElement.setAttribute('src', photoDataUrl);
			/* photoElement.src = photoDataUrl;
			photoElement.style.display = 'block'; */
		} else {
			this.clearPhoto();
		}
	}
}

CustomClientAction.template = 'siantou_emploidutemp.custom_client'

registry.category('actions').add('siantou_emploidutemp.custom_client_action', CustomClientAction)
