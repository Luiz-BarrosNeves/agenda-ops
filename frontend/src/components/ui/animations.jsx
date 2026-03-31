import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Variantes de animação para diferentes tipos de transição
export const fadeVariants = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 }
};

export const slideUpVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
};

export const slideLeftVariants = {
  initial: { opacity: 0, x: 30 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -30 }
};

export const slideRightVariants = {
  initial: { opacity: 0, x: -30 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 30 }
};

export const scaleVariants = {
  initial: { opacity: 0, scale: 0.95 },
  animate: { opacity: 1, scale: 1 },
  exit: { opacity: 0, scale: 0.95 }
};

// Transições configuráveis
export const defaultTransition = {
  duration: 0.2,
  ease: [0.25, 0.1, 0.25, 1]
};

export const smoothTransition = {
  duration: 0.3,
  ease: [0.4, 0, 0.2, 1]
};

export const springTransition = {
  type: 'spring',
  stiffness: 300,
  damping: 30
};

// Componente wrapper para páginas/views
export const PageTransition = ({ children, className = '' }) => (
  <motion.div
    initial="initial"
    animate="animate"
    exit="exit"
    variants={fadeVariants}
    transition={smoothTransition}
    className={className}
  >
    {children}
  </motion.div>
);

// Componente para transição de slide (para mudança de dias)
export const SlideTransition = ({ 
  children, 
  direction = 'left', 
  transitionKey,
  className = '' 
}) => {
  const variants = direction === 'left' ? slideLeftVariants : slideRightVariants;
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={transitionKey}
        initial="initial"
        animate="animate"
        exit="exit"
        variants={variants}
        transition={smoothTransition}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};

// Componente para items em lista com stagger
export const StaggerContainer = ({ children, className = '', delay = 0 }) => (
  <motion.div
    initial="initial"
    animate="animate"
    variants={{
      animate: {
        transition: {
          staggerChildren: 0.05,
          delayChildren: delay
        }
      }
    }}
    className={className}
  >
    {children}
  </motion.div>
);

export const StaggerItem = ({ children, className = '' }) => (
  <motion.div
    variants={slideUpVariants}
    transition={defaultTransition}
    className={className}
  >
    {children}
  </motion.div>
);

// Componente de fade para conteúdo dinâmico
export const FadeIn = ({ children, delay = 0, className = '' }) => (
  <motion.div
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ ...smoothTransition, delay }}
    className={className}
  >
    {children}
  </motion.div>
);

// Animação para cards
export const AnimatedCard = ({ children, className = '', delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, y: 20, scale: 0.98 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    transition={{ ...smoothTransition, delay }}
    whileHover={{ y: -2, transition: { duration: 0.2 } }}
    className={className}
  >
    {children}
  </motion.div>
);

// Animação para botões com feedback
export const AnimatedButton = ({ children, className = '', onClick, ...props }) => (
  <motion.button
    whileHover={{ scale: 1.02 }}
    whileTap={{ scale: 0.98 }}
    transition={{ duration: 0.1 }}
    onClick={onClick}
    className={className}
    {...props}
  >
    {children}
  </motion.button>
);

export default {
  PageTransition,
  SlideTransition,
  StaggerContainer,
  StaggerItem,
  FadeIn,
  AnimatedCard,
  AnimatedButton
};
