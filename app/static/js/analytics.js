/* Analytics load only after opt-in, never on private or payment pages. */
'use strict';
const gaId=document.querySelector('meta[name=ga-measurement-id]')?.content;
const banner=document.querySelector('#analytics-consent');
function enableAnalytics(){if(!/^G-[A-Z0-9]+$/.test(gaId||''))return;window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments);};window.gtag('js',new Date());window.gtag('config',gaId,{anonymize_ip:true,send_page_view:true,page_location:location.origin+location.pathname});const script=document.createElement('script');script.async=true;script.src='https://www.googletagmanager.com/gtag/js?id='+encodeURIComponent(gaId);document.head.append(script);}
let preference='';try{preference=localStorage.getItem('gyanpath-analytics')||'';}catch{}
if(preference==='yes')enableAnalytics();else if(!preference&&banner)banner.hidden=false;
document.querySelectorAll('[data-analytics]').forEach(button=>button.addEventListener('click',()=>{const choice=button.dataset.analytics;try{localStorage.setItem('gyanpath-analytics',choice);}catch{}banner.hidden=true;if(choice==='yes')enableAnalytics();}));
