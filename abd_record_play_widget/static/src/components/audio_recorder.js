// // // /** @odoo-module **/

// // // import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
// // // import { registry } from "@web/core/registry";
// // // import { useService } from "@web/core/utils/hooks";

// // // export class AudioRecorder extends BinaryField {
// // //     static template = "abd_record_play_widget.AudioRecorder";

// // //     get filenameField() {
// // //     // Map binary field to its corresponding filename field
// // //     const fieldMap = {
// // //         'audio_file': 'audio_filename',
// // //         'manager_response_recording': 'manager_response_recording_filename'
// // //     };
// // //     return fieldMap[this.props.name] || `${this.props.name}_filename`;
// // // }

// // //     setup() {
// // //         this.recording = false;
// // //         this.chunks = [];
// // //         this.mediaRecorder = null;
// // //         this.notification = useService("notification"); // For user feedback
// // //     }

// // //     async startRecording() {
// // //         try {
// // //             // Request microphone access
// // //             const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
// // //             this.mediaRecorder = new MediaRecorder(stream);
// // //             this.chunks = [];

// // //             this.mediaRecorder.ondataavailable = (e) => {
// // //                 if (e.data && e.data.size > 0) {
// // //                     this.chunks.push(e.data);
// // //                 } else {
// // //                     console.warn("No data available in MediaRecorder event");
// // //                 }
// // //             };

// // //             // this.mediaRecorder.onstop = async () => {
// // //             //     // Stop all stream tracks to release microphone
// // //             //     this.mediaRecorder.stream.getTracks().forEach(track => track.stop());

// // //             //     // Check if chunks contain valid data
// // //             //     if (!this.chunks.length || this.chunks.every(chunk => chunk.size === 0)) {
// // //             //         this.notification.add("No audio data recorded. Please check your microphone and try again.", {
// // //             //             type: "warning",
// // //             //             title: "Recording Failed",
// // //             //         });
// // //             //         this.recording = false;
// // //             //         this.notify();
// // //             //         return;
// // //             //     }

// // //             //     const blob = new Blob(this.chunks, { type: "audio/webm" });
// // //             //     try {
// // //             //         const base64 = await this.blobToBase64(blob);
// // //             //         if (!base64) {
// // //             //             this.notification.add("Failed to convert audio to base64 format.", {
// // //             //                 type: "danger",
// // //             //                 title: "Processing Error",
// // //             //             });
// // //             //             this.recording = false;
// // //             //             this.notify();
// // //             //             return;
// // //             //         }

// // //             //         // Prepare update object
// // //             //         const updateData = {
// // //             //             [this.props.name]: base64,
// // //             //         };

// // //             //         // Check if audio_filename field exists in the model
// // //             //         if (this.props.record.fields.audio_filename) {
// // //             //             updateData.audio_filename = `recording-${Date.now()}.webm`;
// // //             //         } else {
// // //             //             console.warn("audio_filename field not found in model, skipping filename update");
// // //             //         }

// // //             //         // Update the record

                    




// // //             //         try {
// // //             //             await this.props.record.update(updateData);
// // //             //             await this.props.record.save();
// // //             //         } catch (error) {
// // //             //             console.error("Error updating record:", error);
// // //             //             this.notification.add("Failed to save audio recording to the record.", {
// // //             //                 type: "danger",
// // //             //                 title: "Save Error",
// // //             //             });
// // //             //         }
// // //             //     } catch (error) {
// // //             //         console.error("Error processing audio blob:", error);
// // //             //         this.notification.add("Error processing recorded audio.", {
// // //             //             type: "danger",
// // //             //             title: "Processing Error",
// // //             //         });
// // //             //     }

// // //             //     this.recording = false;
// // //             //     this.notify();
// // //             // };

// // //             this.mediaRecorder.onstop = async () => {
// // //     // Stop all stream tracks to release microphone
// // //     this.mediaRecorder.stream.getTracks().forEach(track => track.stop());

// // //     // Check if chunks contain valid data
// // //     if (!this.chunks.length || this.chunks.every(chunk => chunk.size === 0)) {
// // //         this.notification.add("No audio data recorded. Please check your microphone and try again.", {
// // //             type: "warning",
// // //             title: "Recording Failed",
// // //         });
// // //         this.recording = false;
// // //         this.notify();
// // //         return;
// // //     }

// // //     const blob = new Blob(this.chunks, { type: "audio/webm" });
// // //     try {
// // //         const base64 = await this.blobToBase64(blob);
// // //         if (!base64) {
// // //             this.notification.add("Failed to convert audio to base64 format.", {
// // //                 type: "danger",
// // //                 title: "Processing Error",
// // //             });
// // //             this.recording = false;
// // //             this.notify();
// // //             return;
// // //         }

// // //         // Prepare update object
// // //         const updateData = {
// // //             [this.props.name]: base64,
// // //         };

// // //         // Determine the correct filename field based on which field is being recorded
// // //         let filenameField;
// // //         if (this.props.name === 'audio_file') {
// // //             filenameField = 'audio_filename';
// // //         } else if (this.props.name === 'manager_response_recording') {
// // //             filenameField = 'manager_response_recording_filename';
// // //         } else {
// // //             filenameField = `${this.props.name}_filename`;
// // //         }

// // //         // Only update filename if the field exists in the model
// // //         if (this.props.record.fields[filenameField]) {
// // //             updateData[filenameField] = `recording-${Date.now()}.webm`;
// // //         } else {
// // //             console.warn(`${filenameField} not found in model, skipping filename update`);
// // //         }

// // //         try {
// // //             await this.props.record.update(updateData);
// // //             await this.props.record.save();
// // //             this.notification.add("Recording saved successfully", {
// // //                 type: "success",
// // //                 title: "Success",
// // //             });
// // //         } catch (error) {
// // //             console.error("Error updating record:", error);
// // //             this.notification.add("Failed to save audio recording to the record.", {
// // //                 type: "danger",
// // //                 title: "Save Error",
// // //             });
// // //         }
// // //     } catch (error) {
// // //         console.error("Error processing audio blob:", error);
// // //         this.notification.add("Error processing recorded audio.", {
// // //             type: "danger",
// // //             title: "Processing Error",
// // //         });
// // //     }

// // //     this.recording = false;
// // //     this.notify();
// // // };

// // //             this.mediaRecorder.onerror = (event) => {
// // //                 console.error("MediaRecorder error:", event.error);
// // //                 this.notification.add(`Recording failed: ${event.error.message}`, {
// // //                     type: "danger",
// // //                     title: "Recording Error",
// // //                 });
// // //                 this.recording = false;
// // //                 this.notify();
// // //             };

// // //             this.mediaRecorder.start();
// // //             this.recording = true;
// // //             this.notify();
// // //         } catch (error) {
// // //             console.error("Error starting recording:", error);
// // //             this.notification.add("Failed to access microphone. Please check permissions and ensure your device has a working microphone.", {
// // //                 type: "danger",
// // //                 title: "Microphone Access Error",
// // //             });
// // //             this.recording = false;
// // //             this.notify();
// // //         }
// // //     }

// // //     stopRecording() {
// // //         if (this.mediaRecorder && this.recording) {
// // //             this.mediaRecorder.stop();
// // //         }
// // //     }

// // //     async blobToBase64(blob) {
// // //         if (!blob || blob.size === 0) {
// // //             console.error("Invalid or empty blob");
// // //             return null;
// // //         }

// // //         return new Promise((resolve, reject) => {
// // //             const reader = new FileReader();
// // //             reader.onloadend = () => {
// // //                 if (reader.error) {
// // //                     console.error("FileReader error:", reader.error);
// // //                     reject(reader.error);
// // //                     return;
// // //                 }
// // //                 if (!reader.result || typeof reader.result !== "string") {
// // //                     console.error("FileReader result is empty or invalid");
// // //                     resolve(null);
// // //                     return;
// // //                 }
// // //                 try {
// // //                     const base64Data = reader.result.split(',')[1]; // Remove data:mime;base64,
// // //                     resolve(base64Data);
// // //                 } catch (error) {
// // //                     console.error("Error parsing base64 data:", error);
// // //                     resolve(null);
// // //                 }
// // //             };
// // //             reader.onerror = () => {
// // //                 console.error("FileReader failed:", reader.error);
// // //                 reject(reader.error);
// // //             };
// // //             reader.readAsDataURL(blob);
// // //         });
// // //     }

// // //     get value() {
// // //         return this.props.record.data[this.props.name];
// // //     }

// // //     // getAudioSrcFromRecord() {
// // //     //     const record = this.props.record;
// // //     //     const fieldName = this.props.name;
// // //     //     const base64 = record?.data?.[fieldName];

// // //     //     if (base64 && base64.length > 20) {
// // //     //         // Audio data is base64 and usable
// // //     //         return `data:audio/webm;base64,${base64}`;
// // //     //     }

// // //     //     // Fallback to /web/content URL
// // //     //     const model = record.resModel;
// // //     //     const id = record.resId;
// // //     //     const filename = record.data.audio_filename || 'recording.webm';

// // //     //     if (id && model) {
// // //     //         const encodedFilename = encodeURIComponent(filename);
// // //     //         return `/web/content?model=${model}&id=${id}&field=${fieldName}&filename=${encodedFilename}`;
// // //     //     }

// // //     //     return null;
// // //     // }

// // //     getAudioSrcFromRecord() {
// // //     const record = this.props.record;
// // //     const fieldName = this.props.name;
// // //     const base64 = record?.data?.[fieldName];

// // //     if (base64 && base64.length > 20) {
// // //         return `data:audio/webm;base64,${base64}`;
// // //     }

// // //     // Use the dynamic filename field
// // //     const filename = record.data[this.filenameField] || 'recording.webm';
// // //     const model = record.resModel;
// // //     const id = record.resId;

// // //     if (id && model) {
// // //         const encodedFilename = encodeURIComponent(filename);
// // //         return `/web/content?model=${model}&id=${id}&field=${fieldName}&filename=${encodedFilename}`;
// // //     }

// // //     return null;
// // // }

// // //     notify() {
// // //         // Trigger re-render to update UI
// // //         this.render();
// // //     }
// // // }

// // // export const AudioRecorderField = {
// // //     ...binaryField,
// // //     component: AudioRecorder,
// // // };

// // // registry.category("fields").add("audio_record_widget", AudioRecorderField);








// // /** @odoo-module **/

// // import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
// // import { registry } from "@web/core/registry";
// // import { useService } from "@web/core/utils/hooks";

// // export class AudioRecorder extends BinaryField {
// //     static template = "abd_record_play_widget.AudioRecorder";

// //     setup() {
// //         super.setup();
// //         this.recording = false;
// //         this.chunks = [];
// //         this.mediaRecorder = null;
// //         this.notification = useService("notification");
// //     }

// //     get filenameField() {
// //         // Map binary field to its corresponding filename field
// //         const fieldMap = {
// //             'audio_file': 'audio_filename',
// //             'manager_response_recording': 'manager_response_recording_filename'
// //         };
// //         return fieldMap[this.props.name] || `${this.props.name}_filename`;
// //     }

// //     async startRecording() {
// //         try {
// //             const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
// //             this.mediaRecorder = new MediaRecorder(stream);
// //             this.chunks = [];

// //             this.mediaRecorder.ondataavailable = (e) => {
// //                 if (e.data && e.data.size > 0) {
// //                     this.chunks.push(e.data);
// //                 }
// //             };

// //             this.mediaRecorder.onstop = async () => {
// //                 this.mediaRecorder.stream.getTracks().forEach(track => track.stop());

// //                 if (!this.chunks.length) {
// //                     this.notification.add("No audio data recorded", { type: "warning" });
// //                     return;
// //                 }

// //                 const blob = new Blob(this.chunks, { type: "audio/webm" });
// //                 const base64 = await this.blobToBase64(blob);
                
// //                 const updateData = {
// //                     [this.props.name]: base64,
// //                     [this.filenameField]: `recording-${Date.now()}.webm`
// //                 };

// //                 await this.props.record.update(updateData);
// //                 this.recording = false;
// //                 this.notify();
// //             };

// //             this.mediaRecorder.start(100);
// //             this.recording = true;
// //             this.notify();
// //         } catch (error) {
// //             console.error("Recording failed:", error);
// //             this.notification.add("Could not access microphone. Please check permissions.", {
// //                 type: "danger"
// //             });
// //             this.recording = false;
// //             this.notify();
// //         }
// //     }

// //     stopRecording() {
// //         if (this.mediaRecorder && this.recording) {
// //             this.mediaRecorder.stop();
// //         }
// //     }

// //     async blobToBase64(blob) {
// //         return new Promise((resolve) => {
// //             const reader = new FileReader();
// //             reader.onloadend = () => {
// //                 resolve(reader.result.split(',')[1]);
// //             };
// //             reader.readAsDataURL(blob);
// //         });
// //     }

// //     getAudioSrc() {
// //         const record = this.props.record;
// //         const fieldName = this.props.name;
// //         const base64 = record.data[fieldName];

// //         if (base64 && base64.length > 20) {
// //             return `data:audio/webm;base64,${base64}`;
// //         }

// //         const model = record.resModel;
// //         const id = record.resId;
// //         const filename = record.data[this.filenameField] || 'recording.webm';

// //         if (id && model) {
// //             return `/web/content?model=${model}&id=${id}&field=${fieldName}&filename=${encodeURIComponent(filename)}`;
// //         }

// //         return null;
// //     }

// //     notify() {
// //         this.render();
// //     }
// // }

// // export const AudioRecorderField = {
// //     ...binaryField,
// //     component: AudioRecorder,
// //     supportedTypes: ["binary"],
// // };

// // registry.category("fields").add("audio_record_widget", AudioRecorderField);










// /** @odoo-module **/

// import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
// import { registry } from "@web/core/registry";
// import { useService } from "@web/core/utils/hooks";

// export class AudioRecorder extends BinaryField {
//     static template = "abd_record_play_widget.AudioRecorder";

//     setup() {
//         super.setup();
//         this.recording = false;
//         this.chunks = [];
//         this.mediaRecorder = null;
//         this.notification = useService("notification");
//     }

//     get filenameField() {
//         // Map binary field to its corresponding filename field
//         const fieldMap = {
//             'audio_file': 'audio_filename',
//             'manager_response_recording': 'manager_response_recording_filename'
//         };
//         return fieldMap[this.props.name] || `${this.props.name}_filename`;
//     }

//     async startRecording() {
//         try {
//             const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
//             this.mediaRecorder = new MediaRecorder(stream);
//             this.chunks = [];

//             this.mediaRecorder.ondataavailable = (e) => {
//                 if (e.data && e.data.size > 0) {
//                     this.chunks.push(e.data);
//                 }
//             };

//             this.mediaRecorder.onstop = async () => {
//                 this.mediaRecorder.stream.getTracks().forEach(track => track.stop());

//                 if (!this.chunks.length) {
//                     this.notification.add("No audio data recorded", { type: "warning" });
//                     return;
//                 }

//                 const blob = new Blob(this.chunks, { type: "audio/webm" });
//                 let base64;
//                 try {
//                     base64 = await this.blobToBase64(blob);
//                 } catch (error) {
//                     this.notification.add("Failed to process audio data", { type: "danger" });
//                     console.error("Base64 conversion failed:", error);
//                     this.recording = false;
//                     this.notify();
//                     return;
//                 }

//                 const updateData = {
//                     [this.props.name]: base64
//                 };

//                 // Only add filenameField if it exists in the record
//                 if (this.props.record.fields[this.filenameField]) {
//                     updateData[this.filenameField] = `recording-${Date.now()}.webm`;
//                 } else {
//                     console.warn(`Filename field ${this.filenameField} does not exist in the model.`);
//                 }

//                 console.log("Updating record with:", updateData); // Debug log
//                 try {
//                     await this.props.record.update(updateData);
//                     this.recording = false;
//                     this.notify();
//                 } catch (updateError) {
//                     console.error("Record update failed:", updateError);
//                     this.notification.add("Failed to save recording. Please try again.", {
//                         type: "danger"
//                     });
//                     this.recording = false;
//                     this.notify();
//                 }
//             };

//             this.mediaRecorder.start(100);
//             this.recording = true;
//             this.notify();
//         } catch (error) {
//             console.error("Recording failed:", error);
//             this.notification.add("Could not access microphone. Please check permissions.", {
//                 type: "danger"
//             });
//             this.recording = false;
//             this.notify();
//         }
//     }

//     stopRecording() {
//         if (this.mediaRecorder && this.recording) {
//             this.mediaRecorder.stop();
//         }
//     }

//     async blobToBase64(blob) {
//         try {
//             return new Promise((resolve, reject) => {
//                 const reader = new FileReader();
//                 reader.onloadend = () => {
//                     if (reader.result) {
//                         resolve(reader.result.split(',')[1]);
//                     } else {
//                         reject(new Error("Failed to read blob as Data URL"));
//                     }
//                 };
//                 reader.onerror = () => {
//                     reject(new Error("Error reading blob"));
//                 };
//                 reader.readAsDataURL(blob);
//             });
//         } catch (error) {
//             console.error("blobToBase64 failed:", error);
//             throw error;
//         }
//     }

//     getAudioSrc() {
//         const record = this.props.record;
//         const fieldName = this.props.name;
//         const base64 = record.data[fieldName];

//         if (base64 && base64.length > 20) {
//             return `data:audio/webm;base64,${base64}`;
//         }

//         const model = record.resModel;
//         const id = record.resId;
//         const filename = record.data[this.filenameField] || 'recording.webm';

//         if (id && model) {
//             return `/web/content?model=${model}&id=${id}&field=${fieldName}&filename=${encodeURIComponent(filename)}`;
//         }

//         return null;
//     }

//     notify() {
//         this.render();
//     }
// }

// export const AudioRecorderField = {
//     ...binaryField,
//     component: AudioRecorder,
//     supportedTypes: ["binary"],
// };

// registry.category("fields").add("audio_record_widget", AudioRecorderField);













/** @odoo-module **/

import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AudioRecorder extends BinaryField {
    static template = "abd_record_play_widget.AudioRecorder";

    setup() {
        super.setup();
        this.recording = false;
        this.chunks = [];
        this.mediaRecorder = null;
        this.notification = useService("notification");
    }

    get filenameField() {
        // Map binary field to its corresponding filename field
        const fieldMap = {
            'audio_file': 'audio_filename',
            'manager_response_recording': 'manager_response_recording_filename'
        };
        return fieldMap[this.props.name] || `${this.props.name}_filename`;
    }

    async startRecording() {
        try {
            // Clear previous recording before starting a new one
            const clearData = {
                [this.props.name]: null
            };
            if (this.props.record.fields[this.filenameField]) {
                clearData[this.filenameField] = null;
            }
            await this.props.record.update(clearData);

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.mediaRecorder = new MediaRecorder(stream);
            this.chunks = [];

            this.mediaRecorder.ondataavailable = (e) => {
                if (e.data && e.data.size > 0) {
                    this.chunks.push(e.data);
                }
            };

            this.mediaRecorder.onstop = async () => {
                this.mediaRecorder.stream.getTracks().forEach(track => track.stop());

                if (!this.chunks.length) {
                    this.notification.add("No audio data recorded", { type: "warning" });
                    return;
                }

                const blob = new Blob(this.chunks, { type: "audio/webm" });
                let base64;
                try {
                    base64 = await this.blobToBase64(blob);
                } catch (error) {
                    this.notification.add("Failed to process audio data", { type: "danger" });
                    console.error("Base64 conversion failed:", error);
                    this.recording = false;
                    this.notify();
                    return;
                }

                const updateData = {
                    [this.props.name]: base64
                };

                // Only add filenameField if it exists in the record
                if (this.props.record.fields[this.filenameField]) {
                    updateData[this.filenameField] = `recording-${Date.now()}.webm`;
                } else {
                    console.warn(`Filename field ${this.filenameField} does not exist in the model.`);
                }

                console.log("Updating record with:", updateData);
                try {
                    await this.props.record.update(updateData);
                    this.recording = false;
                    this.notify();
                } catch (updateError) {
                    console.error("Record update failed:", updateError);
                    this.notification.add("Failed to save recording. Please try again.", {
                        type: "danger"
                    });
                    this.recording = false;
                    this.notify();
                }
            };

            this.mediaRecorder.start(100);
            this.recording = true;
            this.notify();
        } catch (error) {
            console.error("Recording failed:", error);
            this.notification.add("Could not access microphone. Please check permissions.", {
                type: "danger"
            });
            this.recording = false;
            this.notify();
        }
    }

    stopRecording() {
        if (this.mediaRecorder && this.recording) {
            this.mediaRecorder.stop();
        }
    }

    async deleteRecording() {
        try {
            const clearData = {
                [this.props.name]: null
            };
            if (this.props.record.fields[this.filenameField]) {
                clearData[this.filenameField] = null;
            }
            console.log("Clearing record with:", clearData);
            await this.props.record.update(clearData);
            this.recording = false;
            this.notify();
            this.notification.add("Recording deleted successfully", { type: "success" });
        } catch (error) {
            console.error("Failed to delete recording:", error);
            this.notification.add("Failed to delete recording. Please try again.", {
                type: "danger"
            });
        }
    }

    async blobToBase64(blob) {
        try {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                    if (reader.result) {
                        resolve(reader.result.split(',')[1]);
                    } else {
                        reject(new Error("Failed to read blob as Data URL"));
                    }
                };
                reader.onerror = () => {
                    reject(new Error("Error reading blob"));
                };
                reader.readAsDataURL(blob);
            });
        } catch (error) {
            console.error("blobToBase64 failed:", error);
            throw error;
        }
    }

    getAudioSrc() {
        const record = this.props.record;
        const fieldName = this.props.name;
        const base64 = record.data[fieldName];

        if (base64 && base64.length > 20) {
            return `data:audio/webm;base64,${base64}`;
        }

        const model = record.resModel;
        const id = record.resId;
        const filename = record.data[this.filenameField] || 'recording.webm';

        if (id && model) {
            return `/web/content?model=${model}&id=${id}&field=${fieldName}&filename=${encodeURIComponent(filename)}`;
        }

        return null;
    }

    notify() {
        this.render();
    }
}

export const AudioRecorderField = {
    ...binaryField,
    component: AudioRecorder,
    supportedTypes: ["binary"],
};

registry.category("fields").add("audio_record_widget", AudioRecorderField);