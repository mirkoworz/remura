import {mountCotHistory} from './cot-history.mjs';
const root=document.querySelector('#cot-history-content');if(root){const p=(new URLSearchParams(location.search).get('symbol')||'XAUUSD').toUpperCase();const symbol=window.REMURA_MARKETS?.symbols?.includes(p)?p:'XAUUSD';mountCotHistory(root,{symbol,fixed:true});}
