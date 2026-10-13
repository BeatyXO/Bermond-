import {createClient,isSuccessful} from 'genlayer-js';
import {studioDevnet} from 'genlayer-js/chains';
import {TransactionHashVariant} from 'genlayer-js/types';
import {contractAddress} from './protocol';
import type {Bond} from './protocol';

type WalletProvider={request:(options:{method:string;params?:unknown[]})=>Promise<unknown>};
declare global {interface Window{ethereum?:WalletProvider}}
const chain=studioDevnet;
const reader=createClient({chain});
function deployed():`0x${string}`{const value=contractAddress();if(!/^0x[a-f\d]{40}$/i.test(value))throw new Error('Bermond is not deployed. Reviewer preview is available without a wallet.');return value as `0x${string}`}
export async function readBondIds():Promise<string[]>{return await reader.readContract({address:deployed(),functionName:'get_bond_ids',args:[],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}) as string[]}
export async function readBond(id:string):Promise<Bond>{return await reader.readContract({address:deployed(),functionName:'get_bond',args:[id],transactionHashVariant:TransactionHashVariant.LATEST_FINAL}) as Bond}
export async function readAllBonds():Promise<Bond[]>{const ids=await readBondIds();return Promise.all(ids.map(readBond))}
export async function walletAddress():Promise<string|null>{if(!window.ethereum)return null;const accounts=await window.ethereum.request({method:'eth_accounts'});return Array.isArray(accounts)&&typeof accounts[0]==='string'?accounts[0]:null}
export async function connectWallet():Promise<string>{const provider=window.ethereum;if(!provider)throw new Error('Install a compatible browser wallet (for example MetaMask or Rabby).');const accounts=await provider.request({method:'eth_requestAccounts'});if(!Array.isArray(accounts)||typeof accounts[0]!=='string')throw new Error('Wallet did not return an account.');const client=createClient({chain,account:accounts[0] as `0x${string}`,provider:provider as never});await client.connect('studioDevnet');return accounts[0]}
export async function writeBond(functionName:string,args:unknown[]=[],value?:bigint):Promise<string>{
  const provider=window.ethereum;if(!provider)throw new Error('Install a compatible wallet before writing.');
  const address=await connectWallet();const client=createClient({chain,account:address as `0x${string}`,provider:provider as never});
  const call={address:deployed(),functionName,args:args as never[],...(value!==undefined?{value}:{})};
  // Development-time profiling. Replace with committed calibrated fee profiles for launch.
  const estimate=await client.estimateTransactionFeesForWrite(call);
  let txHash:`0x${string}`;
  try{txHash=await client.writeContract({...call,fees:{distribution:estimate.distribution,feeValue:estimate.feeValue}})}
  catch(err){throw err}
  // Once a hash is returned NEVER retry blindly on timeout/unknown state.
  const receipt=await client.waitForFinalization({hash:txHash});
  if(!isSuccessful(receipt))throw new Error(`Transaction ${txHash} was not successful: ${receipt.statusName} / ${receipt.txExecutionResultName}. Inspect the receipt before retrying.`);
  return txHash;
}
export const explorerUrl=(hash:string)=>`https://explorer-studio-dev.genlayer.com/tx/${hash}`;