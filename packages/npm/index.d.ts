export interface ParsedAddress {
  flat: string;
  building: string;
  street: string;
  landmark: string;
  area: string;
  city: string;
  state: string;
  pincode: string;
  phone: string;
}

export interface Options {
  /** Ollama server URL. Default http://127.0.0.1:11434 */
  host?: string;
  /** Ollama model name. Default hf.co/abr-6024/indian-address-parser-1.5B-GGUF:Q4_K_M */
  model?: string;
  /** URL of an `india-address-parser serve` HTTP server, e.g. http://localhost:8000. If set, Ollama is not used. */
  apiUrl?: string;
  /** Bearer token for that server, if it was started with an API key. */
  apiKey?: string;
}

export function parseAddress(address: string, options?: Options): Promise<ParsedAddress>;
export function pullModel(options?: Options): Promise<void>;

export class AddressParser {
  constructor(options?: Options);
  parse(address: string): Promise<ParsedAddress>;
  parseMany(addresses: string[]): Promise<ParsedAddress[]>;
}

export const FIELDS: readonly (keyof ParsedAddress)[];
export const SYSTEM: string;
export const DEFAULT_MODEL: string;
export const DEFAULT_HOST: string;
