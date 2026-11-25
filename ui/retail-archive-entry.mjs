import {mountRetailArchive} from './retail-archive.mjs';
const root=document.querySelector('#retail-archive-content');if(root){const requested=(new URLSearchParams(location.search).get('symbol')||'XAUUSD').toUpperCase();const symbol=window.REMURA_MARKETS?.symbols?.includes(requested)?requested:'XAUUSD';mountRetailArchive(root,symbol);}
