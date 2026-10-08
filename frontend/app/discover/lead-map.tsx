"use client";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect } from "react";

type Lead = { id: string; name: string; latitude: number; longitude: number; status: string; severity: string };
function FitBounds({ leads }: { leads: Lead[] }) { const map=useMap(); useEffect(()=>{if(leads.length) map.fitBounds(L.latLngBounds(leads.map(x=>[x.latitude,x.longitude] as [number,number])),{padding:[24,24],maxZoom:14});},[leads,map]); return null; }
function icon(severity: string, status: string, selected: boolean) { const colors:Record<string,string>={critical:"#d94b4b",high:"#ed7c2f",medium:"#d9a62d",low:"#3b9a70",unscanned:"#75839a"}; const glyph=status==="NO_WEBSITE"?"×":status==="DEAD_SITE"?"!":status==="SOCIAL_ONLY"?"S":"W"; return L.divIcon({className:`lead-marker${selected ? " selected" : ""}`,html:`<span style="background:${colors[severity.toLowerCase()]??colors.unscanned}">${glyph}</span>`,iconSize:[30,30],iconAnchor:[15,15]}); }
export default function LeadMap({ leads, selectedId, onSelect }: { leads: Lead[]; selectedId?: string; onSelect: (lead: Lead) => void }) {
  const center: [number,number] = leads[0] ? [leads[0].latitude, leads[0].longitude] : [24.8607, 67.0011];
  return <MapContainer center={center} zoom={11} scrollWheelZoom className="real-map"><TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><FitBounds leads={leads}/>{leads.map(lead=><Marker key={lead.id} position={[lead.latitude,lead.longitude]} icon={icon(lead.severity,lead.status, lead.id === selectedId)} eventHandlers={{click:()=>onSelect(lead)}}><Popup><strong>{lead.name}</strong><br/>{lead.status.replaceAll("_"," ")} · {lead.severity}</Popup></Marker>)}</MapContainer>;
}
