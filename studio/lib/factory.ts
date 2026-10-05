export type WorkerState="running"|"verified"|"blocked"|"idle"|"failed";
export type FactoryWorker={id:string;role:string;state:WorkerState;task:string;receipt?:string};
export type FactorySnapshot={runId:string;status:string;planHash:string;accepted:number;total:number;ready:number;blocked:number;receipts:number;model:string;workers:FactoryWorker[];updatedAt:string};
export const fallbackSnapshot:FactorySnapshot={runId:"offline",status:"disconnected",planHash:"—",accepted:0,total:0,ready:0,blocked:0,receipts:0,model:"not connected",workers:[],updatedAt:new Date(0).toISOString()};
