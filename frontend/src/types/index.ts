export type SlotStatus='AVAILABLE'|'OCCUPIED'|'RESERVED'|'MAINTENANCE';
export interface Slot{slot_id:number;slot_number:string;category_id:number;category:string;status:SlotStatus;current_vehicle_id:number|null}
export interface Stats{total_slots:number;available_slots:number;occupied_slots:number;today_vehicles:number;currently_parked:number;today_revenue:number;occupancy:number;category_breakdown:{category:string;count:number}[]}
export interface ALPRResult{license_plate:string;normalized_plate:string;raw_text:string;confidence:number;status:string;verification_required:boolean;detector:string}
export interface User{ id:number;username:string;name:string;role:string;email:string }
export interface Vehicle{vehicle_id:number;plate_number:string;normalized_plate:string;category_id:number;owner_name?:string|null;owner_phone?:string|null;vehicle_model?:string|null;vehicle_color?:string|null;created_at:string}
export interface ExitResult{record_id:number;license_plate:string;slot:string;entry_time:string;exit_time:string;duration_minutes:number;gross_amount:number;discount_amount:number;net_amount:number;payment_status:string;payment_method:string}
