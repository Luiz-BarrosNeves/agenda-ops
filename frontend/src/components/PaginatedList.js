import React, { useEffect, useRef, useCallback } from 'react';
import { Loader2, ChevronDown } from 'lucide-react';
import { Button } from './ui/button';

/**
 * PaginatedList - A reusable component for infinite scroll or load more pagination
 * 
 * Props:
 * - items: Array of items to render
 * - renderItem: Function to render each item (item, index) => JSX
 * - loading: Boolean indicating loading state
 * - hasMore: Boolean indicating if there are more items to load
 * - onLoadMore: Function to call when loading more items
 * - emptyMessage: Message to show when no items
 * - emptyIcon: Icon component for empty state
 * - className: Additional CSS classes
 * - variant: 'infinite' | 'button' - scroll detection vs button click
 * - gridCols: Number of grid columns (1, 2, 3, 4)
 */
export const PaginatedList = ({
  items = [],
  renderItem,
  loading = false,
  hasMore = false,
  onLoadMore,
  emptyMessage = 'Nenhum item encontrado',
  emptyIcon: EmptyIcon,
  className = '',
  variant = 'button',
  gridCols = 1,
}) => {
  const observerRef = useRef(null);
  const loadMoreRef = useRef(null);

  // Infinite scroll observer
  const handleObserver = useCallback((entries) => {
    const target = entries[0];
    if (target.isIntersecting && hasMore && !loading && variant === 'infinite') {
      onLoadMore?.();
    }
  }, [hasMore, loading, onLoadMore, variant]);

  useEffect(() => {
    if (variant !== 'infinite') return;

    const option = {
      root: null,
      rootMargin: '20px',
      threshold: 0,
    };

    observerRef.current = new IntersectionObserver(handleObserver, option);
    
    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current);
    }

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [handleObserver, variant]);

  // Grid class based on columns
  const gridClass = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 md:grid-cols-2',
    3: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
  }[gridCols] || 'grid-cols-1';

  // Empty state
  if (!loading && items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        {EmptyIcon && (
          <EmptyIcon className="w-12 h-12 text-muted-foreground/30 mb-3" />
        )}
        <p className="text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Items Grid */}
      <div className={`grid ${gridClass} gap-4`}>
        {items.map((item, index) => (
          <div key={item.id || index}>
            {renderItem(item, index)}
          </div>
        ))}
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="flex justify-center py-4">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      )}

      {/* Load more button (for button variant) */}
      {variant === 'button' && hasMore && !loading && (
        <div className="flex justify-center pt-4">
          <Button
            variant="outline"
            onClick={onLoadMore}
            className="gap-2"
          >
            <ChevronDown className="w-4 h-4" />
            Carregar mais
          </Button>
        </div>
      )}

      {/* Infinite scroll trigger element */}
      {variant === 'infinite' && hasMore && (
        <div ref={loadMoreRef} className="h-4" />
      )}

      {/* End of list indicator */}
      {!hasMore && items.length > 0 && (
        <p className="text-center text-sm text-muted-foreground py-4">
          Fim da lista
        </p>
      )}
    </div>
  );
};

/**
 * usePagination - Hook for managing pagination state
 */
export const usePagination = (fetcher, options = {}) => {
  const { 
    pageSize = 20, 
    initialPage = 1,
    autoFetch = true,
  } = options;
  
  const [state, setState] = React.useState({
    items: [],
    page: initialPage,
    total: 0,
    totalPages: 0,
    loading: false,
    error: null,
    hasMore: true,
  });

  const fetchPage = useCallback(async (pageNum, reset = false) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await fetcher(pageNum, pageSize);
      const items = result.items || result.data || result;
      const total = result.total ?? items.length;
      const totalPages = result.total_pages ?? Math.ceil(total / pageSize);
      
      setState(prev => ({
        items: reset ? items : [...prev.items, ...items],
        page: pageNum,
        total,
        totalPages,
        loading: false,
        error: null,
        hasMore: pageNum < totalPages,
      }));
      
      return result;
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        loading: false, 
        error: error.message 
      }));
      throw error;
    }
  }, [fetcher, pageSize]);

  const loadMore = useCallback(() => {
    if (!state.loading && state.hasMore) {
      return fetchPage(state.page + 1);
    }
  }, [state.loading, state.hasMore, state.page, fetchPage]);

  const refresh = useCallback(() => {
    setState(prev => ({ ...prev, items: [], hasMore: true }));
    return fetchPage(1, true);
  }, [fetchPage]);

  const reset = useCallback(() => {
    setState({
      items: [],
      page: initialPage,
      total: 0,
      totalPages: 0,
      loading: false,
      error: null,
      hasMore: true,
    });
  }, [initialPage]);

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      fetchPage(1, true);
    }
  }, []);

  return {
    ...state,
    loadMore,
    refresh,
    reset,
    fetchPage,
  };
};

export default PaginatedList;
