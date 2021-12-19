import React, { useState } from 'react';
import ReactLoading from 'react-loading';

export default function Loading({ loading=true }) {
    if (!loading) return null;
    return (
        <div>
            <ReactLoading type="spin" color="var(--secondary)" height="48px" width="48px"/>
        </div>
    )
}