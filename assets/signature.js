(function(){
  "use strict";
  if(window.ScrollCraft) window.ScrollCraft.mount(document);
  var range=document.getElementById("alignment"),art=document.querySelector(".moire"),steps=[].slice.call(document.querySelectorAll(".chain span"));
  if(!range||!art)return;
  function align(){var v=Number(range.value);art.style.setProperty("--align",String((v-50)*1.65));steps.forEach(function(s,i){s.classList.toggle("is-seen",v>=22+i*19)});range.setAttribute("aria-valuetext",v<35?"Traces apart; public supply is not yet joined to an observation.":v<72?"Traces align; an offering becomes an observation.":"Aligned concept; observation can be preserved as a receipt.");}
  range.addEventListener("input",align);align();
  var count=art.querySelector(".align-value");if(count)range.addEventListener("input",function(){count.textContent=range.value+"%"});
})();
