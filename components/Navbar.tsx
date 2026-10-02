"use client";
import {Box} from "lucide-react";

export default function Navbar(){
  return <header className="nav">
    <a className="brand" href="#">
      <Box size={18}/>
      <span>PIXEL FORGE</span>
    </a>

    <nav>
      <a href="#process">PROCESS</a>
      <a href="#studio">STUDIO</a>
      <a href="https://github.com/utpalchad/pixel_forge" target="_blank" rel="noreferrer">GITHUB ↗</a>
    </nav>

    <a className="navCta" href="#studio">
      <span className="navCtaLabel">START FORGING</span>
      <span className="navCtaIcon">↗</span>
    </a>
  </header>
}
