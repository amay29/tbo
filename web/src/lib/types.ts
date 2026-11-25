export type FstState = "q0" | "q1" | "q2" | "qF";

export type WasteType = "organic" | "inorganic" | "unknown";

export interface BinStatus {
  id: number;
  current_state: FstState;
  organic_fill_pct: number;
  inorganic_fill_pct: number;
  is_full: boolean;
  last_waste_type: WasteType | null;
  updated_at: string;
}

export interface BinEvent {
  id: number;
  created_at: string;
  from_state: FstState;
  input: string;
  output: string;
  to_state: FstState;
  waste_type: WasteType | null;
  organic_fill_pct: number;
  inorganic_fill_pct: number;
}

export interface BinCommand {
  id: number;
  created_at: string;
  command: "force_open";
  processed: boolean;
  processed_at: string | null;
}
