/* Progressive enhancement: unavailable modules leave the local art visible. */
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const lowPower=innerWidth<900||navigator.connection?.saveData||(navigator.hardwareConcurrency&&navigator.hardwareConcurrency<4)||(navigator.deviceMemory&&navigator.deviceMemory<4);
const canvas=document.querySelector('#craft-scene');
if(canvas&&!reduced&&!lowPower){try{
const THREE=await import('https://cdn.jsdelivr.net/npm/three@0.179.1/build/three.module.js');
const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:false,powerPreference:'low-power'});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(45,1,.1,100);camera.position.z=8;
const geometry=new THREE.BufferGeometry(),positions=[];for(let i=0;i<900;i++){const a=i*.31,r=.35+Math.sqrt(i/900)*2.6;positions.push(Math.cos(a)*r,Math.sin(a)*r,Math.sin(a*5)*.25);}geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
const material=new THREE.PointsMaterial({color:0xffe3a3,size:.025,transparent:true,opacity:.55}),points=new THREE.Points(geometry,material);scene.add(points);
const size=()=>{const r=canvas.parentElement.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();};size();const resize=new ResizeObserver(size);resize.observe(canvas.parentElement);
let visible=true,x=0,y=0,frame=0;const observer=new IntersectionObserver(entries=>visible=entries[0].isIntersecting);observer.observe(canvas);canvas.parentElement.addEventListener('pointermove',e=>{const r=canvas.getBoundingClientRect();x=((e.clientX-r.left)/r.width-.5)*.15;y=((e.clientY-r.top)/r.height-.5)*.15;},{passive:true});
function render(){frame=requestAnimationFrame(render);if(document.hidden||!visible)return;points.rotation.z+=.00035;points.rotation.x+=(y-points.rotation.x)*.025;points.rotation.y+=(x-points.rotation.y)*.025;renderer.render(scene,camera);}render();window.addEventListener('pagehide',()=>{cancelAnimationFrame(frame);resize.disconnect();observer.disconnect();geometry.dispose();material.dispose();renderer.dispose();},{once:true});
const load=src=>new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=reject;document.head.append(s);});
await load('https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/gsap.min.js');await load('https://cdn.jsdelivr.net/npm/gsap@3.13.0/dist/ScrollTrigger.min.js');
window.gsap.registerPlugin(window.ScrollTrigger);window.gsap.from('.hero-copy',{y:16,opacity:0,duration:.8,ease:'power2.out'});window.gsap.to('.art-frame>img',{yPercent:5,ease:'none',scrollTrigger:{trigger:'.hero',start:'top top',end:'bottom top',scrub:1}});
const {default:Lenis}=await import('https://cdn.jsdelivr.net/npm/lenis@1.3.8/dist/lenis.mjs');const lenis=new Lenis({duration:.8,smoothWheel:true,anchors:true});lenis.on('scroll',window.ScrollTrigger.update);const tick=time=>lenis.raf(time*1000);window.gsap.ticker.add(tick);window.addEventListener('pagehide',()=>{lenis.destroy();window.gsap.ticker.remove(tick);window.ScrollTrigger.getAll().forEach(x=>x.kill());},{once:true});
}catch{canvas.hidden=true;}}
