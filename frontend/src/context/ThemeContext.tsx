import { createContext, ReactNode, useContext, useEffect, useState } from 'react';

export type Theme = 'dark' | 'light';
type ThemeContextValue = { theme:Theme; toggleTheme:()=>void };

const ThemeContext=createContext<ThemeContextValue>({theme:'dark',toggleTheme:()=>{}});

function savedTheme():Theme{
  try{
    return localStorage.getItem('smart_parking_theme')==='light'?'light':'dark';
  }catch{
    return 'dark';
  }
}

export function ThemeProvider({children}:{children:ReactNode}){
  const [theme,setTheme]=useState<Theme>(savedTheme);
  useEffect(()=>{
    document.documentElement.dataset.theme=theme;
    try{localStorage.setItem('smart_parking_theme',theme)}catch{/* Theme remains available for this session. */}
  },[theme]);
  const toggleTheme=()=>setTheme(current=>current==='dark'?'light':'dark');
  return <ThemeContext.Provider value={{theme,toggleTheme}}>{children}</ThemeContext.Provider>;
}

export const useTheme=()=>useContext(ThemeContext);
