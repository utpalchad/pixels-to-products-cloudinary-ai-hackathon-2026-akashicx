"use client";
import {Canvas,useFrame} from "@react-three/fiber";
import {Environment,Float,OrbitControls} from "@react-three/drei";
import {useRef} from "react";
import * as THREE from "three";

function Form(){
  const group=useRef<THREE.Group>(null);
  useFrame((s,d)=>{
    if(group.current){
      group.current.rotation.y+=d*.08;
      group.current.rotation.x=THREE.MathUtils.lerp(group.current.rotation.x,s.pointer.y*.18,.04);
      group.current.rotation.z=THREE.MathUtils.lerp(group.current.rotation.z,-s.pointer.x*.08,.03);
    }
  });
  return <group ref={group}>
    <Float speed={1.4} rotationIntensity={.22} floatIntensity={.45}>
      <mesh castShadow>
        <torusKnotGeometry args={[1.42,.46,180,28,2,3]}/>
        <meshPhysicalMaterial color="#7c3cff" roughness={.16} metalness={.24} clearcoat={1} clearcoatRoughness={.1}/>
      </mesh>
      <mesh scale={1.018}>
        <torusKnotGeometry args={[1.42,.46,80,16,2,3]}/>
        <meshBasicMaterial color="#ffd400" wireframe transparent opacity={.31}/>
      </mesh>
    </Float>
  </group>
}

export default function ForgeScene(){
  return <Canvas camera={{position:[0,0,5.8],fov:42}} dpr={[1,1.6]}>
    <ambientLight intensity={.7}/>
    <directionalLight position={[3,4,4]} intensity={2.35} color="#ffffff"/>
    <pointLight position={[-3,1,3]} intensity={26} distance={8} color="#ff2d2d"/>
    <pointLight position={[3,-1,2]} intensity={22} distance={8} color="#57e6ff"/>
    <pointLight position={[0,3,-1]} intensity={22} distance={7} color="#ffd400"/>
    <pointLight position={[1,-3,1]} intensity={15} distance={6} color="#ff4fd8"/>
    <Form/>
    <Environment preset="studio"/>
    <OrbitControls enablePan={false} enableZoom={false} autoRotate autoRotateSpeed={.35}/>
  </Canvas>
}
