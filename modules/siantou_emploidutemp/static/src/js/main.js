/** @odoo-module **/

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState, onRendered, onMounted, onWillUnmount } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
const { Component, mount } = owl;

console.log('Welcome to siantou_emploidutemp module');

var siantou_emploidutemp_document_scanner_width = 320;
var siantou_emploidutemp_document_scanner_height = 0;
var siantou_emploidutemp_document_scanner_streaming = false;
var siantou_emploidutemp_document_scanner_video_element = null;
var siantou_emploidutemp_document_scanner_canvas_element = null;
var siantou_emploidutemp_document_photo_canvas_element = null;
var siantou_emploidutemp_document_start_button = null;
var siantou_emploidutemp_document_capture_button = null;
var siantou_emploidutemp_document_stream = null;

export class SiantouEmploidutempDocumentScannerComponent extends Component {
	delay = ms => new Promise(res => setTimeout(res, ms));
	setup() {
		this.state = useState({
			count: 0,
		});
		onRendered(async () => {
			if(!siantou_emploidutemp_document_scanner_video_element || !siantou_emploidutemp_document_scanner_canvas_element || !siantou_emploidutemp_document_photo_canvas_element || !siantou_emploidutemp_document_start_button || !siantou_emploidutemp_document_capture_button) {
				this.getElements();
				console.log('Count :', this.state.count);
				await this.delay(2000);
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
			this.stopWebcam();
			this.removeEventElements();
			this.resetElements();
			console.log('Component unmounted');
		});
	}
	getElements() {
		siantou_emploidutemp_document_scanner_video_element = document.getElementById('siantou_emploidutemp.video_element');
		siantou_emploidutemp_document_scanner_canvas_element = document.getElementById('siantou_emploidutemp.canvas_element');
		siantou_emploidutemp_document_photo_canvas_element = document.getElementById('siantou_emploidutemp.photo_element');
		siantou_emploidutemp_document_start_button = document.getElementById('siantou_emploidutemp.start_button');
		siantou_emploidutemp_document_capture_button = document.getElementById('siantou_emploidutemp.capture_button');
		siantou_emploidutemp_document_stream = null;
		console.log('Get all elements');
	}
	resetElements() {
		siantou_emploidutemp_document_scanner_streaming = false;
		siantou_emploidutemp_document_scanner_video_element = null;
		siantou_emploidutemp_document_scanner_canvas_element = null;
		siantou_emploidutemp_document_photo_canvas_element = null;
		siantou_emploidutemp_document_start_button = null;
		siantou_emploidutemp_document_capture_button = null;
		siantou_emploidutemp_document_stream = null;
		console.log('Reset all elements');
	}
	addEventElements() {
		if(siantou_emploidutemp_document_start_button) {
			siantou_emploidutemp_document_start_button.disabled = false;
			siantou_emploidutemp_document_start_button.addEventListener('click', this.startWebcam, false);
			console.log('Add event listener on start button');
		}
		if(siantou_emploidutemp_document_scanner_video_element) {
			siantou_emploidutemp_document_scanner_video_element.addEventListener('canplay', this.canPlayVideo, false);
			console.log('Add event listener on video element');
		}
		if(siantou_emploidutemp_document_capture_button) {
			siantou_emploidutemp_document_capture_button.addEventListener('click', this.capturePhoto, false);
			console.log('Add event listener on capture button');
		}
	}
	removeEventElements() {
		if(siantou_emploidutemp_document_start_button) {
			siantou_emploidutemp_document_start_button.removeEventListener('click', this.startWebcam);
			console.log('Remove event listener on start button');
		}
		if(siantou_emploidutemp_document_scanner_video_element) {
			siantou_emploidutemp_document_scanner_video_element.removeEventListener('canplay', this.canPlayVideo);
			console.log('Remove event listener on video element');
		}
		if(siantou_emploidutemp_document_capture_button) {
			siantou_emploidutemp_document_capture_button.removeEventListener('click', this.capturePhoto);
			console.log('Remove event listener on capture button');
		}
	}
	stopWebcam() {
		if(siantou_emploidutemp_document_stream) {
			var track = siantou_emploidutemp_document_stream.getTracks()[0];
			track.stop();
			siantou_emploidutemp_document_scanner_video_element.load();
			console.log('Successful stoping video streaming');
		} else {
			console.log('Error stoping video');
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
			siantou_emploidutemp_document_stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
			if(siantou_emploidutemp_document_stream) {
				if(siantou_emploidutemp_document_scanner_video_element) {
					siantou_emploidutemp_document_scanner_video_element.srcObject = siantou_emploidutemp_document_stream;
					siantou_emploidutemp_document_scanner_video_element.play();
					siantou_emploidutemp_document_start_button.disabled = true;
					siantou_emploidutemp_document_capture_button.disabled = false;
					console.log('Successful starting video streaming');
				} else {
					console.log('Error starting video');
				}
			} else {
				console.log('Error starting stream');
			}
		} catch (error) {
			console.log('Error starting webcam :', error);
		}
	}
	canPlayVideo() {
		if (!siantou_emploidutemp_document_scanner_streaming) {
			siantou_emploidutemp_document_scanner_height = siantou_emploidutemp_document_scanner_video_element.videoHeight / (siantou_emploidutemp_document_scanner_video_element.videoWidth / siantou_emploidutemp_document_scanner_width);

			if (isNaN(siantou_emploidutemp_document_scanner_height)) {
				siantou_emploidutemp_document_scanner_height = siantou_emploidutemp_document_scanner_width / (4 / 3);
			}

			siantou_emploidutemp_document_scanner_video_element.setAttribute('width', siantou_emploidutemp_document_scanner_width);
			siantou_emploidutemp_document_scanner_video_element.setAttribute('height', siantou_emploidutemp_document_scanner_height);
			siantou_emploidutemp_document_scanner_canvas_element.setAttribute('width', siantou_emploidutemp_document_scanner_width);
			siantou_emploidutemp_document_scanner_canvas_element.setAttribute('height', siantou_emploidutemp_document_scanner_height);
			siantou_emploidutemp_document_scanner_streaming = true;
		}
	}
	clearPhoto() {
		var context = siantou_emploidutemp_document_scanner_canvas_element.getContext('2d');
		context.fillStyle = "#AAA";
		context.fillRect(0, 0, siantou_emploidutemp_document_scanner_canvas_element.width, siantou_emploidutemp_document_scanner_canvas_element.height);

		const photoDataUrl = siantou_emploidutemp_document_scanner_canvas_element.toDataURL('image/png');
		siantou_emploidutemp_document_photo_canvas_element.setAttribute('src', photoDataUrl);
		/* siantou_emploidutemp_document_photo_canvas_element.src = photoDataUrl;
		siantou_emploidutemp_document_photo_canvas_element.style.display = 'block'; */
	}
	capturePhoto() {
		var context = siantou_emploidutemp_document_scanner_canvas_element.getContext('2d');
		if (siantou_emploidutemp_document_scanner_width && siantou_emploidutemp_document_scanner_height) {
			siantou_emploidutemp_document_scanner_canvas_element.width = siantou_emploidutemp_document_scanner_width;
			siantou_emploidutemp_document_scanner_canvas_element.height = siantou_emploidutemp_document_scanner_height;
			context.drawImage(siantou_emploidutemp_document_scanner_video_element, 0, 0, siantou_emploidutemp_document_scanner_width, siantou_emploidutemp_document_scanner_height);

			const photoDataUrl = siantou_emploidutemp_document_scanner_canvas_element.toDataURL('image/png');
			siantou_emploidutemp_document_photo_canvas_element.setAttribute('src', photoDataUrl);
			/* siantou_emploidutemp_document_photo_canvas_element.src = photoDataUrl;
			siantou_emploidutemp_document_photo_canvas_element.style.display = 'block'; */
		} else {
			this.clearPhoto();
		}
	}
}

SiantouEmploidutempDocumentScannerComponent.template = 'siantou_emploidutemp.document_scanner'

registry.category('actions').add('siantou_emploidutemp.document_scanner', SiantouEmploidutempDocumentScannerComponent)
