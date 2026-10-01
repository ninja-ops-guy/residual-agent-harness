export const REQUIRED_TESTS=103;
const SUMMARY_FIELDS=['tests','pass','fail','skipped','cancelled','todo'];
export function parseTapSummary(log){
  return Object.fromEntries(SUMMARY_FIELDS.map(key=>[key,Number(log.match(new RegExp('^# '+key+' (\\d+)','m'))?.[1]??-1)]));
}
export function qualificationPass({exitCode,counts,syntaxOk,sourceStable}){
  return exitCode===0 && SUMMARY_FIELDS.every(key=>Number.isSafeInteger(counts[key])&&counts[key]>=0) &&
    counts.tests>=REQUIRED_TESTS && counts.pass===counts.tests && counts.fail===0 && counts.skipped===0 &&
    counts.cancelled===0 && counts.todo===0 && syntaxOk===true && sourceStable===true;
}
