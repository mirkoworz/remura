/* REMURA Shark COT Trends UI v1.70 LAB — 23/11/2026 15:01 CET.
 * SVG built via safe DOM, only from CFTC weekly historyFor(). No API calls.
 */
(function(){
  "use strict";
  const core=window.REMURA_SHARK_TRENDS;
  if(!core)return;
  const NS="http://www.w3.org/2000/svg";
  const number=new Intl.NumberFormat("it-IT",{maximumFractionDigits:1});
  const dformat=new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",timeZone:"UTC"});
  const el=(tag,cls,text)=>{
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(text!==undefined)node.textContent=text;
    return node;
  };
  const svgEl=(tag,attrs={})=>{
    const node=document.createElementNS(NS,tag);
    for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));
    return node;
  };
  function render(history,labels=["Gruppo 1","Gruppo 2"]){
    const shell=el("div","cot-trend");
    const model=core.build(history);
    if(model.status!=="READY"){
      shell.append(el("p","trend-message",model.reason||"Grafico N/D: report non confrontabili."));
      return shell;
    }
    const legend=el("div","trend-legend");
    const a=el("span","trend-key first",String(labels[0]||"Categoria 1"));
    const b=el("span","trend-key second",String(labels[1]||"Categoria 2"));
    legend.append(a,b);
    shell.append(legend);
    const box=model.axes;
    const svg=svgEl("svg",{viewBox:"0 0 "+box.width+" "+box.height,
      role:"img","aria-label":"Storico settimanale CFTC reale, "+model.points.length+
      " report: "+String(labels[0]||"categoria A")+" e "+String(labels[1]||"categoria B")+
      ". "+model.gaps+" intervalli non consecutivi. Unità: percentuale di open interest.",
      "preserveAspectRatio":"xMidYMid meet",class:"trend-svg"});
    const minText=svgEl("text",{x:48,y:box.bottom+3,"text-anchor":"end",class:"trend-axis"});
    minText.textContent=number.format(box.low)+"%";
    const maxText=svgEl("text",{x:48,y:box.top+4,"text-anchor":"end",class:"trend-axis"});
    maxText.textContent=number.format(box.high)+"%";
    const startText=svgEl("text",{x:box.left,y:box.height-11,"text-anchor":"start",class:"trend-axis"});
    startText.textContent=dformat.format(new Date(model.startDate+"T12:00:00Z"));
    const endText=svgEl("text",{x:box.right,y:box.height-11,"text-anchor":"end",class:"trend-axis"});
    endText.textContent=dformat.format(new Date(model.endDate+"T12:00:00Z"));
    svg.append(minText,maxText,startText,endText);
    for(const yy of [box.top,box.bottom]){
      svg.append(svgEl("line",{x1:box.left,x2:box.right,y1:yy,y2:yy,class:"trend-grid"}));
    }
    if(box.zeroY!==null){
      svg.append(svgEl("line",{x1:box.left,x2:box.right,y1:box.zeroY,y2:box.zeroY,class:"trend-zero"}));
    }
    for(const series of model.series){
      for(const segment of series.segments){
        if(segment.length>1){
          const poly=svgEl("polyline",{points:segment.map(p=>p.x+","+p.y).join(" "),
            class:"trend-line "+series.key,fill:"none"});
          svg.append(poly);
        }
        for(const p of segment){
          const dot=svgEl("circle",{cx:p.x,cy:p.y,r:3.9,class:"trend-dot "+series.key});
          const tooltip=svgEl("title");
          tooltip.textContent=p.date+" · "+(series.key==="first"?labels[0]:labels[1])+
            " · "+number.format(p.value)+"% OI";
          dot.append(tooltip);
          svg.append(dot);
        }
      }
    }
    shell.append(svg);
    const foot=el("p","trend-caption",model.points.length+" martedì reali · "+
      model.gaps+(model.gaps===1?" intervallo non consecutivo":" intervalli non consecutivi")+
      " · netto % OI, NON prezzo né ordini di acquisto/vendita. "+
      "I tratti separati non vengono collegati; il primo avvistamento della fonte non è attestato.");
    shell.append(foot);
    return shell;
  }
  window.REMURA_SHARK_TRENDS_UI=Object.freeze({render});
})();