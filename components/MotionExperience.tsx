"use client";

import {animate,inView,stagger} from "motion";
import {useEffect} from "react";

const ease=[0.22,1,0.36,1] as const;

export default function MotionExperience(){
  useEffect(()=>{
    if(window.matchMedia("(prefers-reduced-motion: reduce)").matches){
      return;
    }

    const cleanups:Array<()=>void>=[];
    const controls:Array<{stop?:()=>void}>=[];

    const remember=(control:{stop?:()=>void})=>{
      controls.push(control);
      return control;
    };

    // Navigation enters as one composed unit, then its contents settle in.
    remember(animate(
      ".nav",
      {opacity:[0,1],y:[-16,0]},
      {duration:.58,ease}
    ));
    remember(animate(
      ".nav .brand,.nav nav > *,.navCta",
      {opacity:[0,1],y:[-7,0]},
      {duration:.42,ease,delay:stagger(.045,{startDelay:.12})}
    ));

    // Add motion to the system intro without competing with the existing
    // GSAP process-stage choreography.
    const stopProcess=inView(
      ".processIntro",
      ()=>{
        remember(animate(
          ".processIntro > *",
          {opacity:[0,1],y:[24,0]},
          {duration:.7,ease,delay:stagger(.1)}
        ));
      },
      {margin:"0px 0px -12% 0px"}
    );
    cleanups.push(stopProcess);

    // Studio keeps the exact same layout, but its instrument panels assemble
    // into place as the section enters the viewport.
    const stopStudio=inView(
      ".studioWrap",
      ()=>{
        remember(animate(
          ".studioTitle > *",
          {opacity:[0,1],y:[18,0]},
          {duration:.62,ease,delay:stagger(.08)}
        ));
        remember(animate(
          ".studio > *",
          {opacity:[0,1],y:[34,0],scale:[.985,1]},
          {duration:.78,ease,delay:stagger(.09,{startDelay:.08})}
        ));
      },
      {margin:"0px 0px -10% 0px"}
    );
    cleanups.push(stopStudio);

    const stopFooter=inView(
      ".footer",
      ()=>{
        remember(animate(
          ".footer > *",
          {opacity:[0,1],y:[12,0]},
          {duration:.5,ease,delay:stagger(.08)}
        ));
      },
      {margin:"0px 0px -4% 0px"}
    );
    cleanups.push(stopFooter);

    // Motion-powered micro-interactions. These change only transforms/opacity,
    // never layout or the visual design.
    const interactive=Array.from(
      document.querySelectorAll<HTMLElement>(
        ".navCta,.primary,.enhance,.export,.cloudinaryUpload,.formats button,.resultLink,.heroSpecs article"
      )
    );

    const listeners=interactive.map(element=>{
      const enter=()=>{
        if(element.matches(":disabled")) return;
        remember(animate(
          element,
          {scale:1.025,y:-2},
          {duration:.22,ease}
        ));
      };
      const leave=()=>{
        remember(animate(
          element,
          {scale:1,y:0},
          {duration:.3,ease}
        ));
      };
      const down=()=>{
        if(element.matches(":disabled")) return;
        remember(animate(
          element,
          {scale:.975,y:0},
          {duration:.12,ease}
        ));
      };
      const up=()=>{
        if(element.matches(":disabled")) return;
        remember(animate(
          element,
          {scale:1.025,y:-2},
          {duration:.16,ease}
        ));
      };

      element.addEventListener("pointerenter",enter,{passive:true});
      element.addEventListener("pointerleave",leave,{passive:true});
      element.addEventListener("pointerdown",down,{passive:true});
      element.addEventListener("pointerup",up,{passive:true});

      return()=>{
        element.removeEventListener("pointerenter",enter);
        element.removeEventListener("pointerleave",leave);
        element.removeEventListener("pointerdown",down);
        element.removeEventListener("pointerup",up);
      };
    });

    return()=>{
      cleanups.forEach(cleanup=>cleanup());
      listeners.forEach(cleanup=>cleanup());
      controls.forEach(control=>control.stop?.());
    };
  },[]);

  return null;
}
