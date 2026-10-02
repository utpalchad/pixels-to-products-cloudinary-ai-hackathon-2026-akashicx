"use client";
import {Canvas,useFrame} from "@react-three/fiber";
import {Environment,Float,OrbitControls} from "@react-three/drei";
import {useRef} from "react";
import * as THREE from "three";

function Form(){
  const group=useRef<THREE.Group>(null);

  useFrame((s,d)=>{
    if(!group.current) return;
    group.current.rotation.y+=d*.065;
    group.current.rotation.x=THREE.MathUtils.lerp(
      group.current.rotation.x,
      s.pointer.y*.13,
      .035
    );
    group.current.rotation.z=THREE.MathUtils.lerp(
      group.current.rotation.z,
      -s.pointer.x*.06,
      .03
    );
  });

  return <group ref={group}>
    <Float speed={1.25} rotationIntensity={.18} floatIntensity={.38}>
      <mesh castShadow rotation={[.16,.12,0]}>
        <torusKnotGeometry args={[1.44,.43,220,36,2,3]}/>
        <meshPhysicalMaterial
          color="#d9d5ff"
          roughness={.08}
          metalness={.34}
          transmission={.58}
          thickness={1.35}
          ior={1.3}
          clearcoat={1}
          clearcoatRoughness={.04}
          envMapIntensity={1.5}
        />
      </mesh>

      <mesh scale={1.022} rotation={[.16,.12,0]}>
        <torusKnotGeometry args={[1.44,.43,96,18,2,3]}/>
        <meshBasicMaterial
          color="#57e6ff"
          wireframe
          transparent
          opacity={.16}
        />
      </mesh>

      <mesh scale={.58} rotation={[-.22,.35,.4]}>
        <icosahedronGeometry args={[1.08,3]}/>
        <meshPhysicalMaterial
          color="#7c3cff"
          roughness={.12}
          metalness={.5}
          clearcoat={1}
          transparent
          opacity={.62}
        />
      </mesh>
    </Float>
  </group>
}

export default function ForgeScene(){
  return <Canvas
    camera={{position:[0,0,5.9],fov:40}}
    dpr={[1,1.6]}
    gl={{alpha:true,antialias:true}}
  >
    <ambientLight intensity={.52}/>
    <directionalLight position={[3.5,4.5,4]} intensity={2.8} color="#ffffff"/>
    <pointLight position={[-3,1.5,3]} intensity={28} distance={8} color="#ff2d2d"/>
    <pointLight position={[3,-.5,2.5]} intensity={30} distance={8} color="#57e6ff"/>
    <pointLight position={[0,3,-1]} intensity={24} distance={7} color="#ffd400"/>
    <pointLight position={[1,-3,1]} intensity={18} distance={6} color="#ff4fd8"/>
    <Form/>
    <Environment preset="studio"/>
    <OrbitControls
      enablePan={false}
      enableZoom={false}
      autoRotate
      autoRotateSpeed={.22}
    />
  </Canvas>
}
