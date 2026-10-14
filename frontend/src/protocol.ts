export type Dimension = 'allowance' | 'retention' | 'refunds' | 'notice';
export type ClauseStatus = 'UNCHANGED' | 'IMPROVED' | 'BREACHED' | 'UNRESOLVED';
export type BondStatus = 'DRAFT' | 'ACTIVE' | 'UNRESOLVED' | 'BREACHED' | 'CLOSED';
export interface EvidenceReference {source:'baseline'|'current';quote:string;sha256:string}
export interface Clause {dimension:Dimension;status:ClauseStatus;witness:string;evidence?:EvidenceReference[];fact:string}
export interface Assessment {criteria:Clause[];reasoning:string}
export interface Bond {id:string;service_name:string;category:string;provider:string;evidence_assurance?:{baseline:string;baseline_authority?:string;publisher_authentication:string;current_policy:string;historical_authenticity:string};baseline_identity?:{document_id:string;publisher:string;version:string};baseline_url:string;baseline_sha256:string;live_url:string;terms:Record<Dimension,string>;payout_wei:number|string;coverage_ends:number;claim_deadline:number;created_at:number;subscribers:string[];accepted?:string[];enrollment_frozen?:boolean;claimed:string[];funded_wei?:number|string;paid_wei?:number|string;pending_wei?:number|string;reserved_wei:number|string;state:BondStatus;checks:number;last_verdict:string;last_result:Assessment|null;last_check_at:number;policy_fingerprint:string;last_fingerprint:string;released_wei:number|string}
export const DIMENSIONS:Dimension[]=['allowance','retention','refunds','notice'];
export const dimensionName:Record<Dimension,string>={allowance:'Service allowance',retention:'Data retention',refunds:'Refund rights',notice:'Change notice'};
export function formatGen(input:bigint | number | string,precision=3):string{try{const raw=BigInt(input);const whole=raw/10n**18n;const dec=(raw%10n**18n).toString().padStart(18,'0').slice(0,precision).replace(/0+$/,'');return `${whole}${dec?'.'+dec:''} GEN`;}catch{return '— GEN'}}
export function parseGen(input:string):bigint{if(!/^\d+(\.\d{1,18})?$/.test(input.trim()))throw new Error('Enter a GEN amount with up to 18 decimals.');const [whole,frac='']=input.trim().split('.');const amount=BigInt(whole)*10n**18n+BigInt(frac.padEnd(18,'0'));if(amount<=0n)throw new Error('Compensation must be greater than zero.');return amount}
export function short(input:string,size=8):string{return input.length>size*2?input.slice(0,size)+'…'+input.slice(-size):input}
export function formatDate(seconds:number):string{return new Date(seconds*1000).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'})}
export function verdictFromCriteria(input:Clause[]):'BREACHED'|'UNRESOLVED'|'COMPLIANT'{if(input.some(v=>v.status==='BREACHED'))return 'BREACHED';if(input.some(v=>v.status==='UNRESOLVED'))return 'UNRESOLVED';return 'COMPLIANT'}
export function contractAddress():string{return String(import.meta.env.VITE_BERMOND_CONTRACT_ADDRESS||'').trim()}
