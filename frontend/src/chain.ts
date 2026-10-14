import {createClient,isSuccessful} from 'genlayer-js';
import {studioDevnet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import type {TransactionHash} from 'genlayer-js/types';
import {contractAddress} from './protocol';
import type {Bond} from './protocol';

type WalletProvider={request:(options:{method:string;params?:unknown[]})=>Promise<unknown>;on?:(event:string,listener:(value:unknown)=>void)=>void;removeListener?:(event:string,listener:(value:unknown)=>void)=>void};
declare global {interface Window{ethereum?:WalletProvider}}
const chain=studioDevnet;
export const STUDIO_DEV_CHAIN_ID='0xf22d';
const reader=createClient({chain});
export interface PendingWrite {hash:TransactionHash;functionName:string;submittedAt:number;phase:'SUBMITTED'|'ACCEPTED'}
const pendingKey='bermond:pending-write';
const walletDisconnectedKey='bermond:wallet-disconnected';
export function readPendingWrite():PendingWrite|null{try{const raw=localStorage.getItem(pendingKey);if(!raw)return null;const value=JSON.parse(raw) as Partial<PendingWrite>;return typeof value.hash==='string'&&/^0x[a-f\d]{64}$/i.test(value.hash)&&typeof value.functionName==='string'&&typeof value.submittedAt==='number'?{hash:value.hash as TransactionHash,functionName:value.functionName,submittedAt:value.submittedAt,phase:value.phase==='ACCEPTED'?'ACCEPTED':'SUBMITTED'}:null}catch{return null}}
function deployed():`0x${string}`{const value=contractAddress();if(!/^0x[a-f\d]{40}$/i.test(value))throw new Error('Bermond is not deployed. Reviewer preview is available without a wallet.');return value as `0x${string}`}
export async function readBondIds():Promise<string[]>{return await reader.readContract({address:deployed(),functionName:'get_bond_ids',args:[],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}) as string[]}
export async function readBond(id:string):Promise<Bond>{return await reader.readContract({address:deployed(),functionName:'get_bond',args:[id],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}) as unknown as Bond}
export async function readAllBonds():Promise<Bond[]>{const ids=await readBondIds();return Promise.all(ids.map(readBond))}
export async function walletAddress():Promise<string|null>{if(!window.ethereum||localStorage.getItem(walletDisconnectedKey)==='true')return null;const accounts=await window.ethereum.request({method:'eth_accounts'});return Array.isArray(accounts)&&typeof accounts[0]==='string'?accounts[0]:null}
export async function walletNetworkIsStudio():Promise<boolean>{if(!window.ethereum)return false;const chainId=await window.ethereum.request({method:'eth_chainId'});return typeof chainId==='string'&&chainId.toLowerCase()===STUDIO_DEV_CHAIN_ID}
export async function connectWallet():Promise<string>{const provider=window.ethereum;if(!provider)throw new Error('Install a compatible browser wallet (for example MetaMask or Rabby).');const accounts=await provider.request({method:'eth_requestAccounts'});if(!Array.isArray(accounts)||typeof accounts[0]!=='string')throw new Error('Wallet did not return an account.');const chainId=await provider.request({method:'eth_chainId'});if(typeof chainId!=='string'||chainId.toLowerCase()!==STUDIO_DEV_CHAIN_ID)throw new Error('Wrong network. Switch your wallet to GenLayer Studio Dev (chain ID 61997) before connecting or writing.');const client=createClient({chain,account:accounts[0] as `0x${string}`,provider:provider as never});await client.connect('studioDevnet');localStorage.removeItem(walletDisconnectedKey);return accounts[0]}
export function disconnectWallet():void{localStorage.setItem(walletDisconnectedKey,'true')}
function clearPending(hash:TransactionHash,onSubmitted?:(pending:PendingWrite|null)=>void):void{if(readPendingWrite()?.hash===hash){localStorage.removeItem(pendingKey);onSubmitted?.(null)}}
function receiptIsFinalized(receipt:{statusName?:string;lifecycle?:{state?:string}|string}):boolean{const state=typeof receipt.lifecycle==='string'?receipt.lifecycle:receipt.lifecycle?.state;return receipt.statusName?.toUpperCase()==='FINALIZED'||state?.toLowerCase()==='finalized'}
export async function resumePendingWrite():Promise<string>{const pending=readPendingWrite();if(!pending)throw new Error('There is no pending transaction to resume.');const receipt=await reader.waitForFinalization({hash:pending.hash});if(!isSuccessful(receipt)){if(receiptIsFinalized(receipt))localStorage.removeItem(pendingKey);throw new Error(`Transaction ${pending.hash} is ${receipt.statusName} with ${receipt.txExecutionResultName}. It was not a successful finalized write; inspect its receipt before retrying.`)}localStorage.removeItem(pendingKey);return pending.hash}
export async function writeBond(functionName:string,args:unknown[]=[],value?:bigint,onSubmitted?:(pending:PendingWrite|null)=>void):Promise<string>{
  const provider=window.ethereum;if(!provider)throw new Error('Install a compatible wallet before writing.');
  const pending=readPendingWrite();if(pending)throw new Error(`A previous transaction (${pending.hash}) is still pending. Resume its finalization check before submitting another write.`);
  const address=await connectWallet();const client=createClient({chain,account:address as `0x${string}`,provider:provider as never});
  const call={address:deployed(),functionName,args:args as never[],...(value!==undefined?{value}:{})};
  // Development-time profiling. Replace with committed calibrated fee profiles for launch.
  const estimate=await client.estimateTransactionFeesForWrite(call);
  let txHash:TransactionHash;
  try{txHash=await client.writeContract({...call,fees:{distribution:estimate.distribution,feeValue:estimate.feeValue}})}
  catch(err){throw err}
  const submitted:PendingWrite={hash:txHash,functionName,submittedAt:Date.now(),phase:'SUBMITTED'};localStorage.setItem(pendingKey,JSON.stringify(submitted));onSubmitted?.(submitted);
  void client.waitForDecision({hash:txHash}).then(decision=>{if(decision.statusName?.toUpperCase()!=='ACCEPTED')return;const current=readPendingWrite();if(current?.hash!==txHash)return;const accepted={...current,phase:'ACCEPTED' as const};localStorage.setItem(pendingKey,JSON.stringify(accepted));onSubmitted?.(accepted)}).catch(()=>{});
  // Persist before waiting so a timeout or reload can resume this same receipt.
  const receipt=await client.waitForFinalization({hash:txHash});
  if(!isSuccessful(receipt)){if(receiptIsFinalized(receipt))clearPending(txHash,onSubmitted);throw new Error(`Transaction ${txHash} finalized with ${receipt.statusName} / ${receipt.txExecutionResultName}; no successful contract execution was recorded.`)}
  clearPending(txHash,onSubmitted);  return txHash;
}
export const explorerUrl=(hash:string)=>`https://explorer-studio-dev.genlayer.com/tx/${hash}`;
