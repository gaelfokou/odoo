/** @odoo-module **/

import { registry } from "@web/core/registry";
const { Component, whenReady, mount, xml, useRef, useState, onRendered, onMounted, onWillUnmount, onWillStart } = owl;

console.log('Welcome to DocumentScannerComponent component');

var document_scanner_width = 320;
var document_scanner_height = 0;
var document_scanner_streaming = false;
var document_scanner_video_element = null;
var document_scanner_canvas_element = null;
var document_photo_canvas_element = null;
var document_start_button = null;
var document_capture_button = null;
var document_stream = null;

export class DocumentScannerComponent extends Component {
	delay = ms => new Promise(res => setTimeout(res, ms));
	setup() {
		this.state = useState({
			count: 0,
		});
		onRendered(async () => {
			if(!document_scanner_video_element || !document_scanner_canvas_element || !document_photo_canvas_element || !document_start_button || !document_capture_button) {
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
		document_scanner_video_element = document.getElementById('siantou_emploidutemp.video_element');
		document_scanner_canvas_element = document.getElementById('siantou_emploidutemp.canvas_element');
		document_photo_canvas_element = document.getElementById('siantou_emploidutemp.photo_element');
		document_start_button = document.getElementById('siantou_emploidutemp.start_button');
		document_capture_button = document.getElementById('siantou_emploidutemp.capture_button');
		document_stream = null;
		console.log('Get all elements');
	}
	resetElements() {
		document_scanner_streaming = false;
		document_scanner_video_element = null;
		document_scanner_canvas_element = null;
		document_photo_canvas_element = null;
		document_start_button = null;
		document_capture_button = null;
		document_stream = null;
		console.log('Reset all elements');
	}
	addEventElements() {
		if(document_start_button) {
			document_start_button.disabled = false;
			document_start_button.addEventListener('click', this.startWebcam, false);
			console.log('Add event listener on start button');
		}
		if(document_scanner_video_element) {
			document_scanner_video_element.addEventListener('canplay', this.canPlayVideo, false);
			console.log('Add event listener on video element');
		}
		if(document_capture_button) {
			document_capture_button.addEventListener('click', this.capturePhoto, false);
			console.log('Add event listener on capture button');
		}
	}
	removeEventElements() {
		if(document_start_button) {
			document_start_button.removeEventListener('click', this.startWebcam);
			console.log('Remove event listener on start button');
		}
		if(document_scanner_video_element) {
			document_scanner_video_element.removeEventListener('canplay', this.canPlayVideo);
			console.log('Remove event listener on video element');
		}
		if(document_capture_button) {
			document_capture_button.removeEventListener('click', this.capturePhoto);
			console.log('Remove event listener on capture button');
		}
	}
	stopWebcam() {
		if(document_stream) {
			var track = document_stream.getTracks()[0];
			track.stop();
			document_scanner_video_element.load();
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
			document_stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
			if(document_stream) {
				if(document_scanner_video_element) {
					document_scanner_video_element.srcObject = document_stream;
					document_scanner_video_element.play();
					document_start_button.disabled = true;
					document_capture_button.disabled = false;
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
		if (!document_scanner_streaming) {
			document_scanner_height = document_scanner_video_element.videoHeight / (document_scanner_video_element.videoWidth / document_scanner_width);

			if (isNaN(document_scanner_height)) {
				document_scanner_height = document_scanner_width / (4 / 3);
			}

			document_scanner_video_element.setAttribute('width', document_scanner_width);
			document_scanner_video_element.setAttribute('height', document_scanner_height);
			document_scanner_canvas_element.setAttribute('width', document_scanner_width);
			document_scanner_canvas_element.setAttribute('height', document_scanner_height);
			document_scanner_streaming = true;
		}
	}
	clearPhoto() {
		var context = document_scanner_canvas_element.getContext('2d');
		context.fillStyle = "#AAA";
		context.fillRect(0, 0, document_scanner_canvas_element.width, document_scanner_canvas_element.height);

		const photoDataUrl = document_scanner_canvas_element.toDataURL('image/png');
		document_photo_canvas_element.setAttribute('src', photoDataUrl);
		/* document_photo_canvas_element.src = photoDataUrl;
		document_photo_canvas_element.style.display = 'block'; */
	}
	capturePhoto() {
		var context = document_scanner_canvas_element.getContext('2d');
		if (document_scanner_width && document_scanner_height) {
			document_scanner_canvas_element.width = document_scanner_width;
			document_scanner_canvas_element.height = document_scanner_height;
			context.drawImage(document_scanner_video_element, 0, 0, document_scanner_width, document_scanner_height);

			const photoDataUrl = document_scanner_canvas_element.toDataURL('image/png');
			document_photo_canvas_element.setAttribute('src', photoDataUrl);
			/* document_photo_canvas_element.src = photoDataUrl;
			document_photo_canvas_element.style.display = 'block'; */
		} else {
			this.clearPhoto();
		}
	}
}

DocumentScannerComponent.template = 'siantou_emploidutemp.document_scanner'

registry.category('actions').add('siantou_emploidutemp.document_scanner', DocumentScannerComponent)
