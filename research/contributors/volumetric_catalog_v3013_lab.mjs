// REMURA V30.13 LAB — offline candidate catalog. Never writes D1 or enables Telegram.
export const PLATFORMS = Object.freeze(["ATAS","MOTIVEWAVE"]);
export const FEEDS = Object.freeze(["RITHMIC","DXFEED"]);
// Reference roots only, not verified feed-specific tickers or active contracts.
// Currency markets use the native futures quotation, not its reciprocal.
export const ROOTS = Object.freeze({
 "6E":Object.freeze({market:"EURUSD",exchange:"CME",forexReference:"EURUSD",inverse:false}),
 "6B":Object.freeze({market:"GBPUSD",exchange:"CME",forexReference:"GBPUSD",inverse:false}),
 "6J":Object.freeze({market:"JPYUSD",exchange:"CME",forexReference:"USDJPY",inverse:true}),
 "6A":Object.freeze({market:"AUDUSD",exchange:"CME",forexReference:"AUDUSD",inverse:false}),
 "6C":Object.freeze({market:"CADUSD",exchange:"CME",forexReference:"USDCAD",inverse:true}),
 "6S":Object.freeze({market:"CHFUSD",exchange:"CME",forexReference:"USDCHF",inverse:true}),
 "6N":Object.freeze({market:"NZDUSD",exchange:"CME",forexReference:"NZDUSD",inverse:false}),
 "GC":Object.freeze({market:"GC",exchange:"COMEX",forexReference:null,inverse:false}),
 "SI":Object.freeze({market:"SI",exchange:"COMEX",forexReference:null,inverse:false}),
 "NQ":Object.freeze({market:"NQ",exchange:"CME",forexReference:null,inverse:false}),
 "ES":Object.freeze({market:"ES",exchange:"CME",forexReference:null,inverse:false}),
 "CL":Object.freeze({market:"CL",exchange:"NYMEX",forexReference:null,inverse:false})
});
export function buildCatalogCandidate(input){
 if(!input||!PLATFORMS.includes(input.platform)||!FEEDS.includes(input.feed)||
    !Object.hasOwn(ROOTS,input.root))throw Error("unsupported_source_or_root");
 if(typeof input.ticker!=="string"||!/^[A-Z0-9_.-]{1,24}$/.test(input.ticker)||
    input.ticker===input.root||typeof input.contract!=="string"||
    !/^20[2-9][0-9]-(0[1-9]|1[0-2])$/.test(input.contract))
    throw Error("explicit_contract_and_compatible_ticker_required");
 const ref=ROOTS[input.root];
 // Platform is metadata, not a feed. Do not create two rows for the same feed contract.
 const row=Object.freeze({market:ref.market,provider:input.feed,ticker:input.ticker,
    product:"FUTURE",contract:input.contract,source_group:ref.exchange+"_"+input.root,active:0});
 return Object.freeze({row,platform:input.platform,root:input.root,
    quote:"ORIGINAL_FUTURES",forexReference:ref.forexReference,inverse:ref.inverse,
    status:"NEEDS_OWNER_VERIFICATION",telegramEligible:false});
}
