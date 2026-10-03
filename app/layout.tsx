import type { Metadata } from "next";
import Script from "next/script";
import { Space_Grotesk, Syne } from "next/font/google";
import "./globals.css";

const space = Space_Grotesk({
  subsets:["latin"],
  variable:"--font-ui",
  display:"swap"
});

const syne = Syne({
  subsets:["latin"],
  variable:"--font-display",
  weight:["500","600","700","800"],
  display:"swap"
});

export const metadata: Metadata={
  title:"Pixel Forge — Turn Pixels Into Form",
  description:"Transform images into interactive 3D forms, STL, GLB and lithophanes."
};

export default function RootLayout({children}:{children:React.ReactNode}){
  return <html lang="en">
    <body className={`${space.variable} ${syne.variable}`}>
      {children}
      <Script
        src="https://upload-widget.cloudinary.com/latest/global/all.js"
        strategy="afterInteractive"
      />
    </body>
  </html>
}
